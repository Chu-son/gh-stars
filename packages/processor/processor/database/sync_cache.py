"""ローカルSQLiteキャッシュ ↔ リモートDB (MariaDB等) の同期エンジン。

NAS上のDBをマスターとして、ローカルSQLiteキャッシュへ差分を引き込む (pull)。
またタグ編集のリモートへの即時反映 (push_tags) も担当する。

競合ポリシー:
    - 同一リポジトリのタグを複数端末から同時編集した場合は「後勝ち」。
    - 競合を検出した場合は WARNING ログを出力する。
"""
import logging
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .backends.base import DatabaseBackend
    from .backends.sqlite_backend import SQLiteBackend

logger = logging.getLogger(__name__)


class CacheSyncEngine:
    """リモートDB (マスター) からローカルSQLiteキャッシュへの同期エンジン。

    使用例 (MariaDB → ローカルSQLiteキャッシュ構成):
        remote = MariaDBBackend(host="192.168.x.x", ...)
        local = SQLiteBackend("./data/cache.db")
        engine = CacheSyncEngine(remote, local)

        # NASからキャッシュへ差分同期
        count = engine.pull()

        # タグ編集をリモートへ反映
        engine.push_tags(repo_id, tag_names, source="manual")
    """

    def __init__(self, remote_backend: "DatabaseBackend", local_backend: "SQLiteBackend"):
        """
        Args:
            remote_backend: マスターDBのバックエンド (例: MariaDBBackend)
            local_backend: ローカルキャッシュ用 SQLiteBackend
        """
        self.remote = remote_backend
        self.local = local_backend

    def is_remote_available(self) -> bool:
        """リモートDBへの接続可否を確認する。"""
        return self.remote.is_available()

    def pull(self, since: str | None = None) -> int:
        """リモートから差分データをローカルキャッシュへ同期する。

        Args:
            since: 最後の同期日時 (ISO8601文字列)。None の場合は全件同期。
                   未指定時は sync_meta の "cache_pulled_at" を参照する。

        Returns:
            同期されたリポジトリ数。

        Raises:
            Exception: リモートDBへの接続失敗時。
        """
        from processor.database import repository as repo_module

        # 前回の同期時刻を取得 (since が未指定の場合)
        if since is None:
            with self.local.connect() as local_conn:
                since = repo_module.get_sync_meta(local_conn, "cache_pulled_at")

        # リモートからリポジトリを取得
        with self.remote.connect() as remote_conn:
            if since:
                cursor = remote_conn.execute(
                    "SELECT * FROM repositories WHERE synced_at > ?",
                    (since,),
                )
            else:
                cursor = remote_conn.execute("SELECT * FROM repositories")
            repos = [dict(row) for row in cursor.fetchall()]

            # タグ情報を全件取得 (差分管理の複雑さを避けるため全件)
            cursor = remote_conn.execute(
                "SELECT rt.repo_id, t.name, rt.source "
                "FROM repository_tags rt JOIN tags t ON rt.tag_id = t.id"
            )
            raw_tags = cursor.fetchall()

        if not repos:
            logger.info("No new repositories to sync from remote.")
            return 0

        # タグを repo_id でグループ化
        tags_by_repo: dict[str, list[tuple[str, str]]] = {}
        for row in raw_tags:
            if isinstance(row, dict):
                rid, tname, source = row["repo_id"], row["name"], row["source"]
            else:
                rid, tname, source = row[0], row[1], row[2]
            tags_by_repo.setdefault(rid, []).append((tname, source))

        # ローカルへ書き込み
        with self.local.connect() as local_conn:
            for repo in repos:
                repo_module.upsert_repository(local_conn, repo)
                repo_id = repo["github_id"]

                if repo_id in tags_by_repo:
                    auto_tags = [t for t, s in tags_by_repo[repo_id] if s == "auto"]
                    manual_tags = [t for t, s in tags_by_repo[repo_id] if s == "manual"]
                    if auto_tags:
                        repo_module.set_tags_for_repo(
                            local_conn, repo_id, auto_tags, source="auto"
                        )
                    if manual_tags:
                        repo_module.set_tags_for_repo(
                            local_conn, repo_id, manual_tags, source="manual"
                        )

            local_conn.commit()

            # 同期時刻を記録
            pull_time = datetime.now().isoformat()
            repo_module.set_sync_meta(local_conn, "cache_pulled_at", pull_time)
            local_conn.commit()

        logger.info("Cache pull complete: %d repositories synced.", len(repos))
        return len(repos)

    def push_tags(
        self, repo_id: str, tag_names: list[str], source: str
    ) -> None:
        """ローカルでのタグ編集をリモートへ即時反映する (後勝ちポリシー)。

        競合検出: リモートの現在タグとローカルの新しいタグが異なる場合に
        WARNING ログを出力する。リモートへの書き込みは必ず行う (後勝ち)。

        Args:
            repo_id: リポジトリの github_id
            tag_names: 設定するタグ名のリスト
            source: タグのソース ('auto' | 'manual')
        """
        from processor.database import repository as repo_module

        try:
            with self.remote.connect() as remote_conn:
                # 競合検出: リモートの現在タグを取得して比較
                remote_tags = set(repo_module.get_tags_for_repo(remote_conn, repo_id))
                new_tags = set(tag_names)

                if remote_tags and remote_tags != new_tags:
                    logger.warning(
                        "Tag conflict detected for repo '%s': "
                        "remote=%s, overwriting with local=%s",
                        repo_id,
                        sorted(remote_tags),
                        sorted(new_tags),
                    )

                # リモートへ書き込み (後勝ち)
                repo_module.set_tags_for_repo(remote_conn, repo_id, tag_names, source=source)
                remote_conn.commit()

        except Exception as e:
            logger.error(
                "Failed to push tags to remote for repo '%s': %s. "
                "Tags are saved locally only.",
                repo_id,
                e,
            )
