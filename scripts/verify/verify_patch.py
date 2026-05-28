import re
from pathlib import Path

text = Path('C:/yifeGDBOT/src/decision/strategy_engine.py').read_text(encoding='utf-8')

# Find and replace entire should_protect method with stub
old = text[text.find('    def should_protect'):]
# Find next top-level method (exactly 4 spaces indent)
m = re.search(r'\n    def ', old[4:])
if m:
    end = 4 + m.start()
    old_method = old[:end]
    print("OLD METHOD:")
    print(old_method[:300])
    print("---")
    new_method = '''    def should_protect(self, message: Dict, context: Dict) -> bool:
        """T9 patch: disabled"""
        return False
'''
    print("NEW METHOD:", repr(new_method))
else:
    print("Could not find end of method")
