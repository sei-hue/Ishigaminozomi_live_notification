import importlib, traceback

try:
    mod = importlib.import_module('annouce_ishigami')
    importlib.reload(mod)
    print('モジュール読み込み完了。CHANNEL_IDS=', getattr(mod, 'CHANNEL_IDS', None))
    mod.check_all_channels()
    print('チェック実行完了')
except Exception:
    traceback.print_exc()
