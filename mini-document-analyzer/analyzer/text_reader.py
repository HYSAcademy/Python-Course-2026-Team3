import asyncio

async def read_text_file(file_path: str) -> str:
    """
    Asynchronously read a text file. 
    This function uses `asyncio.to_thread` to run the synchronous file reading operation in a separate thread. 
    The file is read with UTF-8 encoding, and the content is returned as a string.
    """
    def _read_sync() -> str:
        with open(file_path, mode="r", encoding="utf-8") as f:
            return f.read()

    return await asyncio.to_thread(_read_sync)