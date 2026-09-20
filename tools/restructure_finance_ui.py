"""One-shot Finance UI package relocation; removed after verification."""
import ast
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = Path('src/ui_qml/modules/project_management')
moves = {}


def add(area, name, group):
    old = BASE / area / 'financials' / name
    moves[old.as_posix()] = (old.parent / group / old.name).as_posix()


for name, group in {
    'billing': 'invoicing', 'budget': 'budgets', 'commitment': 'commitments',
    'cost_entry': 'cost', 'financial_change': 'financial_changes',
    'financial_setup': 'governance', 'forecast': 'forecasts',
    'planned_cost': 'planned_costs', 'rate_card': 'rate_cards',
}.items():
    add('controllers', name + '_domain_event_binder.py', group)
for name in ['lookup', 'mutation', 'refresh', 'selection', 'state', 'types']:
    add('controllers', 'financials_' + name + ('.py' if name == 'types' else '_mixin.py'), 'shared')
for name, group in {
    'audit_builder': 'governance', 'billing_workspace_builder': 'invoicing',
    'change_workspace_builder': 'financial_changes', 'commitment_builder': 'commitments',
    'configuration_builder': 'governance', 'forecast_workspace_builder': 'forecasts',
    'integration_failure_builder': 'cost', 'ledger_builder': 'cost',
    'rate_workspace_builder': 'rate_cards', 'performance_builder': 'reporting',
    'overview_builder': 'shared', 'destination_builder': 'shared',
    'command_handler': 'shared', 'formatters': 'shared', 'selection': 'shared',
    'validation': 'shared',
}.items():
    add('presenters', name + '.py', group)

qmlbase = BASE / 'qml/workspaces/financials'
types = {}
for folder in ['sections', 'dialogs', 'panels']:
    for path in (ROOT / qmlbase / folder).glob('*.qml'):
        name = path.stem
        group = 'shared'
        for token, target in [
            ('Budget', 'budgets'), ('Billing', 'invoicing'), ('Forecast', 'forecasts'),
            ('FinancialChange', 'financial_changes'), ('FinancialsChange', 'financial_changes'),
            ('Rate', 'rate_cards'), ('Actual', 'cost'), ('PostingFailure', 'cost'),
            ('Commitment', 'commitments'), ('PlannedCost', 'planned_costs'),
            ('CostPhasing', 'cost_phasing'), ('Evm', 'earned_value'),
            ('Variance', 'earned_value'), ('Reports', 'reporting'),
            ('CommercialProjection', 'revenue'), ('CostCode', 'governance'),
            ('Profile', 'governance'), ('FinancialSetup', 'governance'),
            ('Activity', 'governance'),
        ]:
            if token in name:
                group = target
                break
        old = path.relative_to(ROOT).as_posix()
        new = (qmlbase / group / folder / path.name).as_posix()
        moves[old] = new
        types[name] = (group, folder)

modules = {old[:-3].replace('/', '.'): new[:-3].replace('/', '.')
           for old, new in moves.items() if old.endswith('.py')}
tracked = subprocess.check_output(['git', 'ls-files'], cwd=ROOT, text=True).splitlines()
for filename in tracked:
    path = ROOT / filename
    if not path.is_file() or path.suffix not in {'.py', '.qml', '.js', '.md', '.toml', '.json', '.txt', '.ps1'}:
        continue
    text = path.read_text(encoding='utf-8-sig')
    original = text
    if path.suffix == '.py':
        # Resolve relative imports using the original package before moving files.
        package = filename[:-3].replace('/', '.').split('.')[:-1]
        tree = ast.parse(text)
        lines = text.splitlines(keepends=True)
        for node in reversed(tree.body):
            if isinstance(node, ast.ImportFrom) and node.level:
                resolved = '.'.join(package[:len(package) - node.level + 1] + (node.module or '').split('.'))
                if resolved in modules or filename in moves:
                    start = node.lineno - 1
                    lines[start] = lines[start].replace('from ' + '.' * node.level + (node.module or '') + ' import', 'from ' + modules.get(resolved, resolved) + ' import')
        text = ''.join(lines)
    for old, new in modules.items():
        text = re.sub(re.escape(old) + r'\b', new, text)
    for old, new in moves.items():
        text = text.replace(old, new)
        # Source-contract tests also construct paths using Path / segments.
        relative_old = old.split('/financials/', 1)[1]
        relative_new = new.split('/financials/', 1)[1]
        if old.endswith('.qml'):
            pattern = r'([\"\x27])financials\1\s*/\s*([\"\x27])' + relative_old.split('/')[0] + r'\2\s*/\s*([\"\x27])' + re.escape(Path(old).name) + r'\3'
            text = re.sub(pattern, '"financials" / ' + ' / '.join('"' + p + '"' for p in relative_new.split('/')), text)
    if path.suffix in {'.qml', '.py'}:
        # Replace aggregate QML imports with only the capability modules used.
        for folder in ['sections', 'dialogs', 'panels']:
            pattern = r'import workspaces\.financials\.' + folder + r' 1\.0(?: as (\w+))?'
            def imports(match):
                alias = match.group(1)
                groups = sorted({g for name, (g, f) in types.items() if f == folder and name in text})
                return '\n'.join('import workspaces.financials.' + g + '.' + folder + ' 1.0' + (' as ' + alias if alias else '') for g in groups)
            text = re.sub(pattern, imports, text)
    if filename in moves and path.suffix == '.qml':
        group, folder = types[path.stem]
        extra = set()
        for name, (g, f) in types.items():
            if (g, f) != (group, folder) and re.search(r'\b' + name + r'\s*\{', text):
                extra.add('import workspaces.financials.' + g + '.' + f + ' 1.0')
        if extra:
            at = text.find('import ')
            text = text[:at] + '\n'.join(sorted(extra)) + '\n' + text[at:]
    if filename == (qmlbase / 'FinancialsWorkspacePage.qml').as_posix():
        text = text.replace('import "dialogs"', 'import "shared/dialogs"').replace('import "panels"', 'import "shared/panels"')
    if text != original:
        path.write_text(text, encoding='utf-8', newline='\n')

for old, new in moves.items():
    source, target = ROOT / old, ROOT / new
    assert source.resolve().is_relative_to(ROOT) and target.resolve().is_relative_to(ROOT)
    assert not target.exists(), new
    target.parent.mkdir(parents=True, exist_ok=True)
    source.rename(target)
    if target.suffix == '.py':
        (target.parent / '__init__.py').touch()

for folder in ['sections', 'dialogs', 'panels']:
    old = ROOT / qmlbase / folder / 'qmldir'
    old.unlink()
    old.parent.rmdir()
for group, folder in sorted(set(types.values())):
    directory = ROOT / qmlbase / group / folder
    entries = ['module workspaces.financials.' + group + '.' + folder]
    entries += [p.stem + ' 1.0 ' + p.name for p in sorted(directory.glob('*.qml'))]
    (directory / 'qmldir').write_text('\n'.join(entries) + '\n', encoding='utf-8')
print(f'Relocated {len(moves)} files without compatibility paths.')
