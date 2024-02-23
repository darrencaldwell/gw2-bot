from types import TracebackType
import pandas
import asyncio

class ReadLock(asyncio.Lock):
    def __init__(self, dataframe: pandas.DataFrame, filename: str):
        self.filename = filename
        self.dataframe = dataframe
        
        super().__init__()

    async def __aenter__(self):
        await super().__aenter__()
        return self.dataframe
    
class EditAndWriteLock:
    def __init__(self, readlock: ReadLock):
        self.readlock = readlock

    async def __aenter__(self):
        return await self.readlock.__aenter__()
    
    async def __aexit__(self, exc_type, exc, tb):
        self.readlock.dataframe.to_csv(self.readlock.filename) #, index = False)
        return await self.readlock.__aexit__(exc_type, exc, tb)


class LockingPandasRWer:
    def __init__(self, filename: str, def_columns: list[str] | None = None):
        self.filename = filename
        
        try:
            self.dataframe = pandas.read_csv(self.filename, index_col=0)

        except pandas.errors.EmptyDataError:
            if def_columns:
                self.dataframe =  pandas.DataFrame(columns=def_columns)

            else:
                self.dataframe = pandas.DataFrame()

        self.read = ReadLock(self.dataframe, self.filename)
        self.edit = EditAndWriteLock(self.read)
        

