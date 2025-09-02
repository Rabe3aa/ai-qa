import boto3
import json
import time
import logging
from typing import Dict, Any, Optional
from openai import OpenAI
from .config import settings
import os

logger = logging.getLogger(__name__)

class EnhancedQAService:
    def __init__(self):
        # Get OpenAI API key from environment or settings (no network calls)
        raw_openai_key = os.getenv("OPENAI_API_KEY") or settings.openai_api_key
        openai_key = raw_openai_key
        # If the env var contains a JSON object (common when storing secrets as JSON), extract the value
        if openai_key and isinstance(openai_key, str):
            cleaned = openai_key.strip()
            if cleaned.startswith("{"):
                try:
                    obj = json.loads(cleaned)
                    if isinstance(obj, dict):
                        # Common keys to look for
                        for k in ("OPENAI_API_KEY", "openai_api_key", "api_key", "key", "OPENAI", "token"):
                            if k in obj and obj[k]:
                                openai_key = obj[k]
                                break
                except Exception:
                    # Leave openai_key as-is if parsing fails
                    pass
            # If wrapped in quotes, strip them
            if isinstance(openai_key, str) and openai_key.startswith('"') and openai_key.endswith('"'):
                openai_key = openai_key.strip('"')

        # Initialize client (avoid logging secrets)
        if not openai_key:
            logger.warning("OpenAI API key is not configured; QA feedback generation may fail.")
        self.openai_client = OpenAI(
            api_key=openai_key,
            max_retries=settings.openai_max_retries,
            timeout=settings.openai_request_timeout_seconds
        )
        
        self.s3_client = boto3.client('s3', region_name=settings.aws_region)
        self.transcribe_client = boto3.client('transcribe', region_name=settings.aws_region)
    
    def start_transcription(self, s3_key: str, job_name: str) -> str:
        """Start AWS Transcribe job"""
        try:
            media_uri = f"s3://{settings.aws_s3_bucket_input}/{s3_key}"
            output_key = f"transcriptions/{job_name}.json"
            
            # Determine media format from file extension (default to 'wav' if unknown)
            ext = os.path.splitext(s3_key)[1].lower().lstrip('.')
            allowed_formats = {'mp3', 'mp4', 'wav', 'flac', 'ogg', 'amr', 'webm', 'm4a'}
            media_format = ext if ext in allowed_formats else 'wav'
            logger.info(f"Starting transcription job {job_name} with media format '{media_format}' for key '{s3_key}'")
            
            self.transcribe_client.start_transcription_job(
                
                TranscriptionJobName=job_name,
                Media={'MediaFileUri': media_uri},
                MediaFormat=media_format,
                LanguageCode='en-US',
                OutputBucketName=settings.aws_s3_bucket_output,
                OutputKey=output_key
            )
            
            logger.info(f"Started transcription job: {job_name}")
            return output_key
            
        except self.transcribe_client.exceptions.ConflictException:
            logger.info(f"Transcription job {job_name} already exists; continuing to poll.")
            return f"transcriptions/{job_name}.json"
        except Exception as e:
            logger.error(f"Failed to start transcription: {e}")
            raise
    
    def get_transcription(self, job_name: str) -> Optional[str]:
        """Poll for transcription completion and return transcript"""
        max_wait = settings.transcribe_max_wait_seconds
        poll_interval = settings.transcribe_poll_interval_seconds
        elapsed = 0
        
        while elapsed < max_wait:
            try:
                response = self.transcribe_client.get_transcription_job(
                    TranscriptionJobName=job_name
                )
                
                status = response['TranscriptionJob']['TranscriptionJobStatus']
                
                if status == 'COMPLETED':
                    # Get transcript from S3
                    output_key = f"transcriptions/{job_name}.json"
                    
                    try:
                        obj = self.s3_client.get_object(
                            Bucket=settings.aws_s3_bucket_output,
                            Key=output_key
                        )
                        transcript_data = json.loads(obj['Body'].read())
                        transcript = transcript_data['results']['transcripts'][0]['transcript']
                        logger.info(f"Transcription completed for job: {job_name}")
                        return transcript
                    except Exception as e:
                        logger.error(f"Failed to retrieve transcript: {e}")
                        time.sleep(poll_interval)
                        elapsed += poll_interval
                        continue
                        
                elif status == 'FAILED':
                    logger.error(f"Transcription failed for job: {job_name}")
                    return None
                else:
                    logger.info(f"Transcription in progress: {status}")
                    time.sleep(poll_interval)
                    elapsed += poll_interval
                    
            except Exception as e:
                logger.error(f"Error polling transcription: {e}")
                time.sleep(poll_interval)
                elapsed += poll_interval
        
        logger.error(f"Transcription timeout for job: {job_name}")
        return None
    
    def correct_transcript(self, transcript: str) -> str:
        """Use OpenAI to correct transcript errors"""
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a transcript correction assistant. Fix grammar, punctuation, and obvious transcription errors while preserving the original meaning and conversational tone. Do not add or remove content, only correct errors."
                    },
                    {
                        "role": "user",
                        "content": f"Please correct this call center transcript:\n\n{transcript}"
                    }
                ],
                temperature=0.1
            )
            
            corrected = response.choices[0].message.content.strip()
            logger.info("Transcript corrected successfully")
            return corrected
            
        except Exception as e:
            logger.error(f"Failed to correct transcript: {e}")
            return transcript
    
    def generate_feedback(self, transcript: str, model: str = "gpt-4o") -> Dict[str, Any]:
        """Generate QA feedback using OpenAI"""
        start_time = time.time()
        
        try:
            response = self.openai_client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are a call center QA analyst. Analyze the call transcript and provide detailed feedback.

Return your analysis as a JSON object with these exact fields:
{
    "agent_summary": "Brief summary of agent performance",
    "qa_scores": {
        "professionalism": 85,
        "communication": 90,
        "problem_solving": 75,
        "compliance": 95,
        "customer_satisfaction": 80
    },
    "qa_feedback": "Detailed feedback with specific examples",
    "overall_score": 85,
    "positive_count": 3,
    "negative_count": 1,
    "neutral_count": 2
}

Scores should be 0-100. Counts should reflect positive, negative, and neutral aspects found."""
                    },
                    {
                        "role": "user",
                        "content": f"Analyze this call transcript:\n\n{transcript}"
                    }
                ],
                temperature=0.3
            )
            
            content = response.choices[0].message.content.strip()
            
            # Parse JSON response
            if content.startswith("```json"):
                content = content[7:-3]
            elif content.startswith("```"):
                content = content[3:-3]
            
            result = json.loads(content)
            result["processing_time_seconds"] = time.time() - start_time
            result["model_used"] = model
            
            logger.info(f"QA analysis completed in {result['processing_time_seconds']:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate QA feedback: {e}")
            return {
                "agent_summary": "Analysis failed",
                "qa_scores": {},
                "qa_feedback": f"Error generating feedback: {str(e)}",
                "overall_score": 0,
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": 0,
                "processing_time_seconds": time.time() - start_time,
                "model_used": model
            }
