"""Utils for communicating over a websocket"""

from typing import List, Union, Optional, Callable, Generator
import asyncio
from threading import Thread
import queue
import json
import os

import websockets
import pandas as pd
from fastapi import WebSocket, WebSocketDisconnect

from ytpa_utils.df_utils import df_dt_codec

from .constants import WS_STREAM_TERM_MSG, WS_MAX_RECORDS_SEND
from .misc_utils import df_gen_from_queue, wait_on_qsize

TESTING = os.environ.get('RUN_API_TESTS') == 'yes'

if TESTING:
    from .constants import WS_RECORDS_TESTING, WS_DFS_TESTING, DF_GEN_QUEUE_TESTING

    def rec_gen_test():
        for df in WS_RECORDS_TESTING:
            yield df
    RECORD_GEN_TEST = rec_gen_test()

    def df_gen_test():
        for df in WS_DFS_TESTING:
            yield df
    DF_GEN_TEST = df_gen_test()




""" General-purpose methods """
async def gen_next_records(gen, websocket: WebSocket):
    """
    Get next record from a generator if possible, otherwise send stream termination signal and shut down websocket.
    """
    try:
        return next(gen)
    except:
        # clean up and disconnect
        if not TESTING:
            await websocket.send_json(WS_STREAM_TERM_MSG)
        else:
            DF_GEN_QUEUE_TESTING.put(WS_STREAM_TERM_MSG)
        raise WebSocketDisconnect

async def send_df_via_websocket(df: pd.DataFrame,
                                transformations: dict,
                                websocket: WebSocket):
    """Send DataFrame in pieces over websocket"""
    i = 0
    while not (df_ := df.iloc[i * WS_MAX_RECORDS_SEND: (i + 1) * WS_MAX_RECORDS_SEND]).empty:
        # apply transformations to specified columns
        if transformations is not None:
            cnvs = {key: val for key, val in transformations.items() if key in df_.columns}
            df_dt_codec(df_, cnvs)  # make it JSONifiable

        # pack DataFrame into list of dictionaries
        data_send: List[dict] = df_.to_dict('records')

        # send data over websocket
        if not TESTING:
            await websocket.send_json(data_send)
        else:
            DF_GEN_QUEUE_TESTING.put(data_send)

        # increment pointer
        i += 1

    # send empty list signifying that entire DataFrame has been sent
    if not TESTING:
        await websocket.send_json([])
    else:
        DF_GEN_QUEUE_TESTING.put([])





""" Send DataFrames over websocket """
async def run_websocket_stream_server(websocket: WebSocket,
                                      setup_df_gen: Callable,
                                      transformations: Optional[dict] = None):
    """
    Run websocket stream that generates DataFrames.

    setup_df_gen is a function that returns a DataFrame generator and a database engine. The engine is destroyed before
    exiting to ensure that db connections are not left dangling.
    """
    df_gen, engine = None, None
    try:
        while True:
            # receive JSON data
            data_recv = await websocket.receive_json() if not TESTING else None

            # initialize DataFrame generator first time around
            if df_gen is None:
                df_gen, engine = setup_df_gen(data_recv) if not TESTING else (DF_GEN_TEST, None)

            # generate the next DataFrame
            df = await gen_next_records(df_gen, websocket)

            # send DataFrame via websocket
            await send_df_via_websocket(df, transformations, websocket) # send DataFrame in chunks
    except WebSocketDisconnect as e:
        del df_gen, engine
        print(e)





""" Client-side (generate DataFrames through websocket) """
async def get_next_msg(websocket: websockets.connect) -> Optional[List[dict]]:
    """Receive next message over websocket"""
    # receive data
    if not TESTING:
        data_recv = await websocket.recv()
    else:
        data_recv = next(RECORD_GEN_TEST)
    data_recv: Union[List[dict], str] = json.loads(data_recv) # subframe of DataFrame, stream termination string, or empty list
    assert isinstance(data_recv, (list, str))

    # check for stream termination message
    if data_recv == WS_STREAM_TERM_MSG:
        raise StopIteration

    # check for empty list indicating end of DataFrame
    if len(data_recv) == 0:
        return

    return data_recv

async def receive_msgs(websocket: websockets.connect,
                       q: asyncio.Queue):
    """
    Receive sequence of data messages over websocket connection, stitch them into a DataFrame, place them in a queue.
    """
    data_recv_all = []
    while 1:
        data_recv = await get_next_msg(websocket)
        if data_recv is not None: # in middle of subframe
            data_recv_all += data_recv
        else: # finished getting DataFrame
            df = pd.DataFrame.from_dict(data_recv_all)
            await q.put(df)
            return

async def stream_dfs_websocket_subfunc(q: asyncio.Queue,
                                       websocket: Optional[WebSocket] = None,
                                       msg_to_send_str: Optional[str] = None,
                                       max_qsize: Optional[int] = None):
    """Testing branch for stream_dfs_websocket()."""
    try:
        while 1:
            if not TESTING:
                await websocket.send(msg_to_send_str)
            await receive_msgs(websocket, q)
            await wait_on_qsize(q, max_qsize)
    except Exception as e:
        print(e)
        await q.put(None)

async def stream_dfs_websocket(endpoint: str,
                               msg_to_send: dict,
                               q: asyncio.Queue,
                               max_qsize: Optional[int] = None):
    """Stream DataFrames through a websocket into a queue."""
    if TESTING:
        await stream_dfs_websocket_subfunc(q, max_qsize=max_qsize)
    else:
        msg_to_send_str = json.dumps(msg_to_send)
        async with websockets.connect(endpoint) as websocket:
            await stream_dfs_websocket_subfunc(q,
                                               websocket=websocket,
                                               msg_to_send_str=msg_to_send_str,
                                               max_qsize=max_qsize)

def run_dfs_stream_with_options(endpoint: str,
                                msg_to_send: dict,
                                df_processor: Optional[Callable],
                                q_stream: asyncio.Queue,
                                max_qsize: Optional[int] = None):
    """
    Simultaneously stream data from an API endpoint through a websocket and process it.

    endpoint: url to connect to
    msg_to_send: the request body to send
    df_processor: coroutine that processes the DataFrames as they are placed in the queue
    q_stream: asyncio Queue to use for storing DataFrames
    """
    async def run_tasks():
        async with asyncio.TaskGroup() as tg:
            if df_processor is not None:
                tg.create_task(df_processor(q_stream))
            tg.create_task(stream_dfs_websocket(endpoint,
                                                msg_to_send,
                                                q_stream,
                                                max_qsize=max_qsize))
    asyncio.run(run_tasks())

def df_generator_ws(endpoint: str,
                    msg_to_send: dict,
                    transformations: Optional[dict] = None) \
        -> Generator[pd.DataFrame, None, None]:
    """Wrapper for websocket-based DataFrame generator"""
    max_qsize = 5

    q_gen = queue.Queue()

    # spin up websocket thread with between-queue handoff process
    async def df_processor(q_stream_: asyncio.Queue):
        """Pass DataFrames from asynchronous to synchronous queues."""
        while 1:
            df = await q_stream_.get()
            if df is not None and transformations is not None:
                cnvs = {key: val for key, val in transformations.items() if key in df.columns}
                df_dt_codec(df, cnvs)
            q_gen.put(df)
            if df is None:
                return
            await wait_on_qsize(q_gen, max_qsize)

    q_stream = asyncio.Queue()
    df_gen_thread = Thread(
        target=run_dfs_stream_with_options,
        daemon=True,
        args=(endpoint, msg_to_send, df_processor, q_stream, max_qsize)
    )
    df_gen_thread.start()

    # initiate DataFrame generator
    df_gen = df_gen_from_queue(q_gen)

    return df_gen

