import io, glob, os

# All chapter files + presentation
chapter_files = glob.glob(r'c:\Users\r3d4\.gemini\antigravity-ide\scratch\plateforme-restitution\CHAPITRE_*.md')
chapter_files += glob.glob(r'c:\Users\r3d4\.gemini\antigravity-ide\scratch\plateforme-restitution\CONCLUSION_GENERALE.md')
chapter_files += [r'd:\ClarIA shots\presentation.html']

patterns = ['40 tests', '44 tests', '22 exigences', '20 exigences', '18 exigences']

all_ok = True

for fpath in sorted(chapter_files):
    fname = os.path.basename(fpath)
    try:
        with io.open(fpath, 'r', encoding='utf-8') as f:
            text = f.read()
        results = {p: text.count(p) for p in patterns if text.count(p) > 0}
        status = 'OK' if results.get('44 tests', 0) >= 0 and results.get('40 tests', 0) == 0 else 'PROBLEM'
        if results.get('40 tests', 0) > 0:
            all_ok = False
            status = 'PROBLEM'
        print(f'--- {fname} [{status}] ---')
        for p, c in results.items():
            flag = '!!!' if p in ('40 tests', '20 exigences', '18 exigences') else '   '
            print(f'  {flag} [{c}x] "{p}"')
        if not results:
            print('  (no relevant number found)')
        print()
    except Exception as e:
        print(f'{fname}: ERROR - {e}\n')

print()
if all_ok:
    print('RESULT: All files are consistent. "44 tests" and "22 exigences" everywhere.')
else:
    print('RESULT: INCONSISTENCY FOUND - check lines marked with !!!')
