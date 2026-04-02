from textual.widgets import Input

class SearchInput(Input):
    """
    検索バー専用の入力コンポーネント。
    Tabキーでのフォーカス移動から除外され、'/' キーでのみフォーカスされるように制御します。
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 初期状態は Tab でのフォーカスを不可にする
        self.can_focus = False

    def on_blur(self) -> None:
        """フォーカスが外れた際（EnterやTab、マウス操作など）、再び Tab の対象外に戻します。"""
        self.can_focus = False
