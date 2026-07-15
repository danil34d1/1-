#!/usr/bin/env python3
from __future__ import annotations
import json,re,sys
from datetime import date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PRODUCTS=ROOT/'data'/'products'
ID_RE=re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
STATUSES={'needs-verification','verified','deprecated'}
CATEGORIES={'unknown','surfactant','detergent','soap','builder','solvent','additive','finished-product'}
REQUIRED={'id','display_name','status','category','source_records','confirmed_facts','hypotheses','next_verification','notes','updated_at'}
SECRET_PATTERNS=[re.compile(r'gh[pousr]_[A-Za-z0-9]{20,}'),re.compile(r'AKIA[0-9A-Z]{16}'),re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')]

def valid_date(value):
    try: date.fromisoformat(value); return True
    except (TypeError,ValueError): return False

def validate(path):
    errors=[]
    try:
        raw=path.read_text(encoding='utf-8'); item=json.loads(raw)
    except Exception as exc: return [f'{path}: invalid JSON: {exc}']
    if any(p.search(raw) for p in SECRET_PATTERNS): errors.append(f'{path}: possible secret')
    if set(item)!=REQUIRED: errors.append(f'{path}: required keys mismatch')
    if not isinstance(item.get('id'),str) or not ID_RE.fullmatch(item['id']): errors.append(f'{path}: invalid id')
    elif path.stem!=item['id']: errors.append(f'{path}: filename and id differ')
    if item.get('status') not in STATUSES: errors.append(f'{path}: invalid status')
    if item.get('category') not in CATEGORIES: errors.append(f'{path}: invalid category')
    if not item.get('source_records'): errors.append(f'{path}: source required')
    if not valid_date(item.get('updated_at')): errors.append(f'{path}: invalid updated_at')
    if item.get('status')=='verified' and not item.get('confirmed_facts'): errors.append(f'{path}: verified requires confirmed_facts')
    if item.get('status')=='needs-verification' and not item.get('next_verification'): errors.append(f'{path}: verification steps required')
    return errors

def main():
    paths=sorted(PRODUCTS.glob('*.json'))
    errors=[e for path in paths for e in validate(path)]
    if not paths: errors.append('no product records')
    if errors:
        print('\n'.join(f'ERROR: {e}' for e in errors),file=sys.stderr); return 1
    print(f'Catalog validation passed: {len(paths)} record(s)'); return 0

if __name__=='__main__': raise SystemExit(main())
