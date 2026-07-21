import asyncio
from backend.core.database import AsyncSessionLocal
from backend.models.file import File as FileModel
from sqlalchemy import select
from backend.services.file_validator import read_excel_safe, build_preview_rows, read_csv_safe

async def main():
    async with AsyncSessionLocal() as db:
        files = (await db.execute(select(FileModel))).scalars().all()
        for f in files:
            if not f.preview_rows:
                try:
                    print(f"Backfilling {f.original_filename}...")
                    with open(f.storage_path, "rb") as file_obj:
                        raw_bytes = file_obj.read()
                    if f.file_type in ("xlsx", "xls"):
                        df, _ = read_excel_safe(raw_bytes, sheet_name=f.sheet_name)
                    else:
                        df = read_csv_safe(raw_bytes)
                    f.preview_rows = build_preview_rows(df)
                except Exception as e:
                    print(f"Failed on {f.original_filename}:", e)
        await db.commit()
        print("Done!")

if __name__ == "__main__":
    asyncio.run(main())
