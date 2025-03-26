#!/usr/bin/env python
import asyncio
import websockets
import json
import pyaudio

# Audio configuration
CHUNK_DURATION = 0.1  # seconds
SAMPLE_RATE = 16000
CHANNELS = 1
FORMAT = pyaudio.paInt16
CHUNK_SIZE = int(SAMPLE_RATE * CHUNK_DURATION)

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

    async with websockets.connect(uri) as websocket:
        # Send the initial mode to the server to setup the VAD model
        await websocket.send("online")
        print("Connected to server, starting audio streaming...")

        try:
            while True:
                # Read a chunk of audio from the microphone
                audio_data = stream.read(CHUNK_SIZE)

                # Send the audio chunk to the server
                await websocket.send(audio_data)

                # Receive EPD result from the server
                response = await websocket.recv()
                try:
                    result = json.loads(response)
                except json.JSONDecodeError:
                    result = response
                print("Server response:", result)
        except websockets.exceptions.ConnectionClosed:
            print("Server closed the connection.")
        finally:
            # Clean up the audio stream and PyAudio instance
            stream.stop_stream()
            stream.close()
            p.terminate()

if __name__ == '__main__':
    # Server URI (modify as needed)
    uri = "ws://localhost:8001"
    asyncio.run(audio_client(uri))
