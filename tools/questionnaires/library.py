"""Read-only local questionnaire catalogue; never reads personal instances."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "questionnaires" / "instruments"


def load():
    records = [json.loads(p.read_text()) for p in sorted(ROOT.glob("*.json"))]
    result = {}
    for record in records:
        key = f"{record['id']}@{record['version']}"
        if key in result:
            raise ValueError(f"Duplicate version: {key}")
        result[key] = record
    return result


def validate(records):
    for key, record in records.items():
        assert record['schema_version'] == 1, key
        assert record['limitations'] and record['status'] == 'provisional', key
        fields = record['form']['fields']
        assert fields and len({f['key'] for f in fields}) == len(fields), key
        rule = record['scoring']
        if rule['method'] == 'sum_option_indices':
            field = fields[0]
            maximum = sum(len(item['o'] if isinstance(item, dict) else field['options']) - 1
                          for item in field['items'])
            assert rule['range'] == [0, maximum], key
            assert all(0 <= i < len(field['items']) for i in rule['reverse_item_indices']), key
        assert 'answers' not in record and 'prefill' not in record, key


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['list', 'show', 'compose', 'validate'])
    parser.add_argument('ids', nargs='*', help='Exact id@version, e.g. pss10@1.0.0')
    args = parser.parse_args()
    records = load()
    validate(records)
    if args.command == 'validate':
        print(f'Validated {len(records)} questionnaire definitions.')
    elif args.command == 'list':
        for key, record in records.items():
            print(f"{key}\t{record['title']}\t{record['status']}")
    else:
        if not args.ids or (args.command == 'show' and len(args.ids) != 1):
            parser.error('show requires one id@version; compose requires at least one.')
        if len(set(args.ids)) != len(args.ids):
            parser.error('Duplicate modules are not allowed.')
        unknown = set(args.ids) - records.keys()
        if unknown:
            parser.error('Unknown version: ' + ', '.join(sorted(unknown)))
        selected = [records[key] for key in args.ids]
        keys = [f['key'] for r in selected for f in r['form']['fields']]
        if len(keys) != len(set(keys)):
            parser.error('Selected modules have conflicting field keys.')
        output = selected[0] if args.command == 'show' else {
            'schema_version': 1, 'instruments': selected,
            'response_storage': 'instances/<name>/private/questionnaires/',
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
