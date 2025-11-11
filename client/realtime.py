#!/usr/bin/env python
# encoding: utf-8
# Copyright (c) 2025- SATURN
# AUTHORS:
# Sukbong Kwon (Galois)

import sys
import asyncio
import websockets
import json
import pyaudio
import numpy as np
import uuid
import argparse

# Audio configuration
CHUNK_DURATION = 0.1  # seconds
TTS_STATUS_SIZE = 1  # bytes
SAMPLE_RATE = 16000
CHANNELS = 1
FORMAT = pyaudio.paInt16
CHUNK_SIZE = int(SAMPLE_RATE * CHUNK_DURATION)

# Scaling factor to adjust microphone amplitude on macOS
SCALING_FACTOR = 0.5

async def audio_client(url):
    print(f"Connecting to server at {url}...")
    # Initialize PyAudio
    p = pyaudio.PyAudio()
    stream = None

    try:
        # Open the microphone stream with the desired settings
        stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK_SIZE
        )

        transcribed_text = ""

        async with websockets.connect(url) as websocket:
            # Send configuration string to server first (required by server protocol)
            config_string = "mode=agent"
            await websocket.send(config_string)

            # Wait for server to send session_id
            response = await websocket.recv()
            try:
                result = json.loads(response)
                if result.get('status') != 'READY' or 'session_id' not in result:
                    print(f"Unexpected server response: {result}")
                    return

                session_id = result['session_id']
                # Convert hex string to bytes for use as session header
                session_id_bytes = uuid.UUID(session_id).bytes
                print(f"Received session ID from server: {session_id}")
            except json.JSONDecodeError:
                print(f"Failed to parse server response: {response}")
                return

            # Use the session_id received from server (as bytes)
            session_header = session_id_bytes
            tts_status = 0
            n = 0  # Counter for the number of chunks sent

            try:
                while True:
                    # Read a chunk of audio from the microphone
                    audio_data = stream.read(CHUNK_SIZE, exception_on_overflow=False)

                    #================================================================================================
                    # CAUTION: macOS specific fix

                    # Convert raw audio bytes to a NumPy array of int16
                    audio_np = np.frombuffer(audio_data, dtype=np.int16)
                    # Apply a scaling factor to adjust the amplitude (fixes macOS misbehavior)
                    audio_np = (audio_np * SCALING_FACTOR).astype(np.int16)
                    # Convert the scaled NumPy array back to bytes
                    scaled_audio_data = audio_np.tobytes()

                    #================================================================================================

                    # Add session_id and tts_status to the chunk data as bytes
                    chunk_data = session_header + tts_status.to_bytes(TTS_STATUS_SIZE, 'big') + scaled_audio_data

                    # Send the audio chunk to the server
                    await websocket.send(chunk_data)

                    # Receive VAD result from the server
                    response = await websocket.recv()
                    print(f"Server response ({n}):", response)

                    try:
                        result = json.loads(response)
                    except json.JSONDecodeError:
                        result = response

                    status = result.get('status')
                    text = result.get('text')

                    # 5) 실시간 텍스트 업데이트
                    if text:
                        transcribed_text = text
                        # "\r"로 같은 줄에 덮어쓰기, "\033[K"로 커서 이후 클리어
                        sys.stdout.write("\r" + transcribed_text + "\033[K")
                        sys.stdout.flush()

                    # 6) status==3 이면 최종 문장으로 간주하고 클라이언트 종료
                    if status == 3:
                        if transcribed_text:
                            sys.stdout.write("\r" + transcribed_text + "\033[K")
                            sys.stdout.flush()
                            print()  # 줄 바꿈
                        print("Status 3 received. Terminating client...")
                        break

                    n += 1

                    # Add a delay to simulate real-time streaming
                    await asyncio.sleep(0.05)

            except websockets.exceptions.ConnectionClosed:
                print("Server closed the connection.")
            finally:
                # Clean up the audio stream and PyAudio instance
                stream.stop_stream()
                stream.close()
                p.terminate()

            # Send close signal to server
            print("Sending close signal to server...")
            await websocket.send("close")

            # Wait for the server to send the concatenated file path
            print("Waiting for server to send concatenated audio file...")
            try:
                # Set a timeout for receiving the file path
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                result = json.loads(response)
                print(result)
            except asyncio.TimeoutError:
                print("Timeout waiting for server to send file path")
            except websockets.exceptions.ConnectionClosed:
                print("Connection closed before receiving file path")

            # Close the websocket connection
            await websocket.close()
            print("WebSocket connection closed.")
    except (ConnectionRefusedError, OSError) as e:
        print(f"Connection error: {e}")
        print("Please check if the server is running and the URL is correct.")
    except Exception as e:
        print(f"Error: {e}")
        raise
    finally:
        # Clean up the audio stream and PyAudio instance
        if stream is not None:
            stream.stop_stream()
            stream.close()
        p.terminate()

def main():
    parser = argparse.ArgumentParser(description="Real-time Audio Client for VAD")
    parser.add_argument(
        '--url',
        type=str,
        default='ws://api.magovoice.com:9009',
        # default='wss://api.magovoice.com/epdy/',
        help='WebSocket server URL',
    )
    args = parser.parse_args()

    try:
        asyncio.run(audio_client(args.url))
    except KeyboardInterrupt:
        print("\nClient stopped.")
    finally:
        print("Exiting...")

if __name__ == '__main__':
    main()
