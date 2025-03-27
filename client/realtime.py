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

# Audio configuration
CHUNK_DURATION = 0.1  # seconds
SAMPLE_RATE = 16000
CHANNELS = 1
FORMAT = pyaudio.paInt16
CHUNK_SIZE = int(SAMPLE_RATE * CHUNK_DURATION)

# Scaling factor to adjust microphone amplitude on macOS
SCALING_FACTOR = 0.5

async def audio_client(uri):
    # Initialize PyAudio
    p = pyaudio.PyAudio()

    # Open the microphone stream with the desired settings
    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=CHUNK_SIZE
    )

    transcribed_text = ""

    async with websockets.connect(uri) as websocket:
        # Send the initial mode to the server to setup the VAD model
        await websocket.send("online")
        print("Connected to server, starting audio streaming...")

        try:
            while True:
                # Read a chunk of audio from the microphone
                audio_data = stream.read(CHUNK_SIZE)

                #================================================================================================
                # CAUTION: macOS specific fix

                # Convert raw audio bytes to a NumPy array of int16
                audio_np = np.frombuffer(audio_data, dtype=np.int16)
                # Apply a scaling factor to adjust the amplitude (fixes macOS misbehavior)
                audio_np = (audio_np * SCALING_FACTOR).astype(np.int16)
                # Convert the scaled NumPy array back to bytes
                scaled_audio_data = audio_np.tobytes()

                #================================================================================================

                # Send the audio chunk to the server
                await websocket.send(scaled_audio_data)

                # Receive EPD result from the server
                response = await websocket.recv()
                try:
                    result = json.loads(response)
                except json.JSONDecodeError:
                    result = response

                # print("Server response:", result)

                # If there is a "text" field in the result, append it to transcribed_text.
                if isinstance(result, dict):
                    if "text" in result:
                        transcribed_text = result["text"]
                        # Clear the line and update with new transcribed_text.
                        sys.stdout.write("\r" + transcribed_text + "\033[K")
                        sys.stdout.flush()
                    if "status" in result and result["status"] == 3 and transcribed_text:
                        # When status==3, print the final text on a new line and reset.
                        sys.stdout.write("\r" + transcribed_text + "\033[K")
                        sys.stdout.flush()
                        print()  # New line.
                        transcribed_text = ""


        except websockets.exceptions.ConnectionClosed:
            print("Server closed the connection.")
        finally:
            # Clean up the audio stream and PyAudio instance
            stream.stop_stream()
            stream.close()
            p.terminate()

if __name__ == '__main__':
    # Server URI (modify as needed)
    uri = "ws://10.7.105.242:8001"
    asyncio.run(audio_client(uri))
