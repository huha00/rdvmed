
import asyncio
import os
import sys

import aiohttp
from dotenv import load_dotenv
from loguru import logger
from PIL import Image
from runner import configure

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    BotStoppedSpeakingFrame,
    Frame,
    OutputImageRawFrame,
    SpriteFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIObserver, RTVIProcessor
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.transports.services.daily import DailyParams, DailyTransport, DailyTranscriptionSettings
from pipecat.services.llm_service import FunctionCallParams

from gcalendar import get_calendar_events
from gcalendar import add_calendar_event
from gcalendar import is_valid_iso_datetime, now_utc2

load_dotenv(override=True)
logger.remove(0)
logger.add(sys.stderr, level="DEBUG")


class IntakeProcessor:
    def __init__(self, context: OpenAILLMContext):
        print(f"Initializing context from IntakeProcessor")
        
        ev = get_calendar_events()
        now = now_utc2()
        content = "Vous êtes Emma, une agente d'une entreprise appelée ServiceMed. Votre travail consiste à planifier un rendez-vous médical de 30 minutes. Vous parlez avec Hugo. Vous devez vous adresser à l'utilisateur par son prénom et rester polie et professionnelle. Vous n'êtes pas une professionnelle de santé, donc vous ne devez donner aucun conseil médical. Gardez vos réponses courtes. Votre rôle est de planifier un rendez-vous. Ne faites pas de suppositions sur les valeurs à utiliser dans les fonctions. Demandez des précisions si la réponse de l'utilisateur est ambiguë. Nous sommes le " + now + ". Les créneaux qui ne sont pas disponibles sont : " + ev + "Commencez par vous présenter. Appelez la fonction create_event une fois que vous vous êtes mis d'accord avec l'utilisateur sur la date et l'heure du rendez-vous."
        print("Context given to robot:", content)

        context.add_message(
            {
                "role": "system",
                "content": content
            }
        )
        
        context.set_tools(
            [
                {
                    "type": "function",
                    "function": {
                        "name": "create_event",
                        "description": "Utilisez cette fonction pour enregistrer le rendez-vous médical du médecin dans le calendrier.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "date": {
                                    "type": "string",
                                    "description": "La date et l'heure du rendez-vous. L'utilisateur peut les fournir dans n'importe quel format, mais convertissez-les au format YYYY-MM-DDTHH:MM:SS pour appeler cette fonction."
                                }
                            },
                        },
                    },
                }
            ]
        )

    async def create_event(self, params: FunctionCallParams):
        print("create_event called!!!!!")
        print(params.arguments["date"])
        start_date_iso_str = params.arguments["date"]
        
        if is_valid_iso_datetime(start_date_iso_str):
            
            print("iso date is valid, adding calendar event...")
            add_calendar_event(start_date_iso_str)
            print("calendar event added successfully!")
            
            await params.result_callback(
                [
                    {
                        "role": "system",
                        "content": "Informez l'utilisateur que le rendez-vous a été pris. Remerciez-le et dites-lui au revoir."
                    }
                ]
            )
        else:
            # The user provided an incorrect birthday; ask them to try again
            await params.result_callback(
                [
                    {
                        "role": "system",
                        "content": "Il y a un problème technique. Demandez à l'utilisateur de rappeler plus tard, remerciez-le et dites-lui au revoir."
                    }
                ]
            )


async def main():
    """Main bot execution function.

    Sets up and runs the bot pipeline including:
    - Daily video transport
    - Speech-to-text and text-to-speech services
    - Language model integration
    - Animation processing
    - RTVI event handling
    """
    async with aiohttp.ClientSession() as session:
        (room_url, token) = await configure(session)

        # Set up Daily transport with video/audio parameters
        transport = DailyTransport(
            room_url,
            token,
            "Chatbot",
            DailyParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                vad_analyzer=SileroVADAnalyzer(),
                transcription_enabled=True,
                transcription_settings=DailyTranscriptionSettings(
                     language="fr",
                     model="nova-2-general"
                )
            ),
        )

        print("Eleven labs api key", os.getenv("ELEVENLABS_API_KEY"))

        # Initialize text-to-speech service
        tts = ElevenLabsTTSService(
            api_key=os.getenv("ELEVENLABS_API_KEY"),
            model="eleven_multilingual_v2",
            voice_id="rbFGGoDXFHtVghjHuS3E",
        )

        # Initialize LLM service
        llm = OpenAILLMService(
            api_key=os.getenv("OPENAI_API_KEY"),
        )

        # Set up conversation context and management
        # The context_aggregator will automatically collect conversation context
        messages = []
        context = OpenAILLMContext(messages=messages)
        context_aggregator = llm.create_context_aggregator(context)

        intake = IntakeProcessor(context)
        llm.register_function("create_event", intake.create_event)
        #
        # RTVI events for Pipecat client UI
        #
        rtvi = RTVIProcessor(config=RTVIConfig(config=[]))

        pipeline = Pipeline(
            [
                transport.input(),
                rtvi,
                context_aggregator.user(),
                llm,
                tts,
                transport.output(),
                context_aggregator.assistant(),
            ]
        )

        task = PipelineTask(
            pipeline,
            params=PipelineParams(
                allow_interruptions=True,
                enable_metrics=True,
                enable_usage_metrics=True,
            ),
            observers=[RTVIObserver(rtvi)],
        )

        @rtvi.event_handler("on_client_ready")
        async def on_client_ready(rtvi):
            await rtvi.set_bot_ready()
            # Kick off the conversation
            print("conversation kicked off")
            await task.queue_frames([context_aggregator.user().get_context_frame()])

        @transport.event_handler("on_first_participant_joined")
        async def on_first_participant_joined(transport, participant):
            await transport.capture_participant_transcription(participant["id"])

        @transport.event_handler("on_participant_left")
        async def on_participant_left(transport, participant, reason):
            print(f"Participant left: {participant}")
            await task.cancel()


        runner = PipelineRunner()

        await runner.run(task)


if __name__ == "__main__":
    asyncio.run(main())
