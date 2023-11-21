import asyncio
from typing import Generator, Optional

import pandas as pd


def df_gen_from_queue(q) -> Generator[pd.DataFrame, None, None]:
    """DataFrame generator that pulls from a queue."""
    while 1:
        df = q.get()
        if df is None:
            return
        yield df


async def wait_on_qsize(q: asyncio.Queue,
                        max_qsize: Optional[int] = None):
    """Wait until queue is small enough."""
    if max_qsize is None:
        return
    while q.qsize() >= max_qsize:
        await asyncio.sleep(0.01)


async def process_dfs_stream(q_stream: asyncio.Queue,
                             options: Optional[dict] = None):
    """Process DataFrames from a queue until a None is found"""
    # options
    if options is None:
        options = {}
    print_dfs = options.get('print_df')
    print_count = options.get('print_count')
    q_stats = options.get('q_stats')

    # process stream
    count = 0
    while 1:
        df = await q_stream.get()
        if df is None:
            return
        count += len(df)
        if print_dfs:
            print(df)
        if print_count:
            print(f"Records count so far: {count}.")
        if q_stats:
            q_stats.put({'count': count})
