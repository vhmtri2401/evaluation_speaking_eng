# pronunciation_assessment.py

import re
import torch
from transformers import WhisperProcessor, WhisperForConditionalGeneration
from g2p_en import G2p
import nltk
import librosa
import soundfile as sf
import json
import os
from jiwer import wer, cer
import numpy as np
from nltk.tokenize import word_tokenize
import logging


# Tải các gói cần thiết
nltk.download('punkt')

# Thiết lập logger
logger = logging.getLogger(__name__)

from textblob import TextBlob

def get_grammar_errors_and_grammar_scores(text):
    blob = TextBlob(text)
    corrected_blob = blob.correct()
    original_words = blob.words
    corrected_words = corrected_blob.words
    total_words = len(original_words)
    
    grammar_errors = sum(1 for o, c in zip(original_words, corrected_words) if o.lower() != c.lower())
    if total_words == 0:
        grammar_score = 0.0
    else:
        grammar_score = ((total_words - grammar_errors) / total_words) * 100
    return grammar_errors, grammar_score


def lexical_diversity(text):
    words = word_tokenize(text)
    if len(words) == 0:
        diversity_score = 0.0
    else:
        diversity_score = (len(set(words)) / len(words)) * 100 
    return diversity_score

def pronunciation_assessment_configured_with_whisper(filename, language, reference_text, processor, model, device):
    logger.info(f"Starting pronunciation assessment for file: {filename}")
    try:
        def preprocess_text(text):
            text = text.lower()
            text = re.sub(r'[^\w\s]', '', text)
            return text

        def text_to_phonemes(text):
            g2p = G2p()
            phonemes = g2p(text)
            phonemes = [p for p in phonemes if p != ' ']
            return phonemes

        def calculate_per(transcribed_phonemes, reference_phonemes):
            distance = nltk.edit_distance(transcribed_phonemes, reference_phonemes)
            max_length = max(len(transcribed_phonemes), len(reference_phonemes))
            if max_length == 0:
                phoneme_error_rate_ = 0.0
            else:
                phoneme_error_rate = distance / max_length
                phoneme_error_rate_ = (1 - phoneme_error_rate) * 100  
            return phoneme_error_rate_

        def calculate_wer_cer(transcription, reference):
            wer_score = wer(reference, transcription) * 100
            cer_score = cer(reference, transcription) * 100
            return wer_score, cer_score

        def analyze_intonation(filename, sampling_rate):
            y, sr = librosa.load(filename, sr=sampling_rate)
            pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
            pitches = pitches[magnitudes > np.median(magnitudes)]
            if len(pitches) == 0:
                return 0.0
            average_pitch = np.mean(pitches)
            return float(average_pitch)

        # Load and process audio
        logger.info(f"Loading audio file: {filename}")
        speech_array, sampling_rate = librosa.load(filename, sr=16000)
        duration = librosa.get_duration(y=speech_array, sr=sampling_rate)
        logger.info(f"Audio duration: {duration:.2f} seconds")

        # Process the entire audio file without segmentation
        logger.info("Processing entire audio file without segmentation.")

        # Transcribe the entire audio
        input_features = processor(speech_array, sampling_rate=16000, return_tensors="pt").input_features
        input_features = input_features.to(device)

        with torch.no_grad():
            predicted_ids = model.generate(input_features)
        transcription = processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]
        transcription_processed = preprocess_text(transcription)
        reference_processed = preprocess_text(reference_text)

        logger.info(f"Transcription: {transcription_processed}")

        # Convert to phonemes
        transcription_phonemes = text_to_phonemes(transcription_processed)
        reference_phonemes = text_to_phonemes(reference_processed)

        # Calculate PER
        phoneme_error_rate = calculate_per(transcription_phonemes, reference_phonemes)
        logger.info(f"Phoneme Error Rate (PER): {phoneme_error_rate:.2f}%")

        # Calculate WER and CER
        wer_score, cer_score = calculate_wer_cer(transcription_processed, reference_processed)
        logger.info(f"Word Error Rate (WER): {wer_score:.2f}%")
        logger.info(f"Character Error Rate (CER): {cer_score:.2f}%")

        # Analyze intonation
        average_pitch = analyze_intonation(filename, 16000)
        logger.info(f"Average Pitch: {average_pitch:.2f} Hz")

        # Calculate other scores
        accuracy = phoneme_error_rate  
        fluency = max(0.0, 100.0 - wer_score)  
        prosody_score = average_pitch / 300.0  
        completeness = max(0.0, 100.0 - cer_score)  
        avg_pro_score = phoneme_error_rate  

        # Grammar and lexical diversity
        grammar_errors, grammar_score = get_grammar_errors_and_grammar_scores(transcription_processed)
        lex_diversity = lexical_diversity(transcription_processed)
        logger.info(f"Grammar Errors: {grammar_errors}")
        logger.info(f"Grammar Score: {grammar_score:.2f}%")
        logger.info(f"Lexical Diversity: {lex_diversity:.2f}%")

        # Final assessment result
        final_pronunciation_assessment_result = {
            'PronunciationAssessment': {
                'AccuracyScore': float(accuracy),
                'FluencyScore': float(fluency),
                'ProsodyScore': float(prosody_score),
                'CompletenessScore': float(completeness),
                'PronScore': float(avg_pro_score),
                'Intonation': float(average_pitch)
            },
            'GrammarAssessment': {
                'GrammarErrors': int(grammar_errors),
                'GrammarScore': float(grammar_score)
            },
            'LexicalDiversity': float(lex_diversity)
        }

        logger.info("Pronunciation assessment completed successfully.")
        return final_pronunciation_assessment_result

    except Exception as e:
        logger.error(f"Exception in pronunciation_assessment_configured_with_whisper: {e}")
        return {"msg": str(e)}
