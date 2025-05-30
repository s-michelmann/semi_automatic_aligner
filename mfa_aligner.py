#!/usr/bin/env python3
"""
MFA Wrapper - Handles interaction with Montreal Forced Aligner
"""
import json
import logging
import subprocess
import tempfile
import shutil
import csv
import os
import sys
import re
import signal
import time
import wave  # Add this import
from pathlib import Path
import soundfile as sf
import numpy as np
from typing import Callable, Dict, Optional
import atexit
import weakref
import contextlib

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global registry of temporary directories to clean up
_temp_dirs_to_cleanup = set()

def _cleanup_temp_dirs():
    """Clean up all registered temporary directories"""
    global _temp_dirs_to_cleanup
    for temp_dir in _temp_dirs_to_cleanup:
        try:
            if temp_dir and Path(temp_dir).exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
                logger.info(f"Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            logger.error(f"Error cleaning up temporary directory {temp_dir}: {e}")
    _temp_dirs_to_cleanup.clear()

# Register cleanup on normal exit
atexit.register(_cleanup_temp_dirs)

# Register cleanup on signals
for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
    try:
        signal.signal(sig, lambda s, f: (_cleanup_temp_dirs(), sys.exit(1)))
    except (AttributeError, ValueError):
        # Some signals might not be available on all platforms
        pass

@contextlib.contextmanager
def temp_directory():
    temp_dir = Path(tempfile.mkdtemp())
    _temp_dirs_to_cleanup.add(str(temp_dir))  # Use add() for sets, convert Path to string
    try:
        yield temp_dir
    finally:
        _cleanup_temp_dirs()

def load_config(config_path=None):
    """Load configuration from a JSON file
    
    Args:
        config_path: Path to configuration file (optional)
        
    Returns:
        dict: Configuration dictionary
    """
    # Default configuration
    default_config = {
        "dictionary_path": "~/Documents/MFA/pretrained_models/dictionary/english_us_arpa.dict",
        "acoustic_model_path": "english_us_arpa",
        "use_pretrained_acoustic": True
    }
    
    # If no config path provided, look in standard locations
    if not config_path:
        # Check in user's home directory
        home_config = os.path.expanduser("~/.mfa_config.json")
        # Check in current directory
        local_config = "mfa_config.json"
        
        if os.path.exists(home_config):
            config_path = home_config
        elif os.path.exists(local_config):
            config_path = local_config
    
    # If config path exists, load it
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                # Update default config with user config
                default_config.update(user_config)
                logger.info(f"Loaded configuration from {config_path}")
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
    
    return default_config

class MFAWrapper:
    """Wrapper for Montreal Forced Aligner"""
    
    def __init__(self, audiofile=None, textfile=None, temp_path=None, cache_dir=None, 
                 dictionary_path=None, acoustic_model_path=None, use_pretrained_acoustic=None):
        """Initialize the aligner
        
        Args:
            audiofile: Path to audio file (for compatibility with semi_align.py)
            textfile: Path to text file (for compatibility with semi_align.py)
            temp_path: Path to use as temporary directory
            cache_dir: Path to use for caching models
            dictionary_path: Path to dictionary file (overrides default)
            acoustic_model_path: Path or name of acoustic model (overrides default)
            use_pretrained_acoustic: Whether to use a pretrained model (overrides default)
        """
        # Store cache directory
        self.cache_dir = Path(cache_dir) if cache_dir else None
        
        # Create temporary directory if not provided
        if temp_path:
            self.temp_dir = Path(temp_path)
        else:
            self.temp_dir = Path(tempfile.mkdtemp())
            _temp_dirs_to_cleanup.add(str(self.temp_dir))
        
        logger.info(f"Using temporary directory: {self.temp_dir}")
        
        # Initialize with default models - use full paths
        # Default paths that can be overridden
        self.dictionary_path = dictionary_path or "~/Documents/MFA/pretrained_models/dictionary/english_us_arpa.dict"
        self.acoustic_model_path = acoustic_model_path or "english_us_arpa"
        self.use_pretrained_acoustic = use_pretrained_acoustic if use_pretrained_acoustic is not None else True
        
        # Expand user directory (~ symbol)
        self.dictionary_path = os.path.expanduser(self.dictionary_path)
    
        
        # For compatibility with semi_align.py
        self.audio = None
        self.all_aligned_words = []
        self.audio_sel = (0, -1)
        self.aligned_words = []
        self.selected_words = []
        
        # Initialize audio and text if provided
        if audiofile and textfile:
            self.initialize_from_files(audiofile, textfile)
    
    def initialize_from_files(self, audiofile, textfile):
        """Initialize from audio and text files (for compatibility with semi_align.py)
        
        Args:
            audiofile: Path to audio file
            textfile: Path to text file
        """
        # Open audio file
        self.audio = wave.open(audiofile, mode='rb')
        
        # Read text file
        with open(textfile, 'r') as texthandle:
            text = texthandle.read()
        
        # Split text into words
        all_words = text.split()
        self.all_aligned_words = []
        tmpid = 0
        
        # Initialize all aligned words with None 
        for ww in all_words:
            idstring = "w" + str(tmpid)
            self.all_aligned_words.append((idstring, ww.lower(), None, None))
            tmpid += 1
    
    def align_all(self):
        """Align all words in the text (for compatibility with semi_align.py)"""
        self.align_segment((0, -1), (0, None))
    
    def align_segment(self, audio_sel, word_sel):
        """Align a segment of audio to a selection of words (for compatibility with semi_align.py)
        
        Args:
            audio_sel: Tuple of (start_time, end_time) in seconds
            word_sel: Tuple of (start_index, end_index) in words list
            
        Returns:
            List of aligned words with timing information
        """
        self.audio_sel = audio_sel
        self.selected_words = self.all_aligned_words[word_sel[0]:word_sel[1]]
        
        # Write temporary files
        audio_path = self.write_audio_selection()
        text_path = self.write_text_selection()
        
        # Run alignment
        try:
            # Run MFA alignment
            alignment_results = self.align(audio_path, text_path)
            
            # Convert MFA results to the format expected by semi_align.py
            words = []
            for word_info in alignment_results.get('words', []):
                # Skip silence markers
                if word_info.get('word', '').lower() in ['sp', 'sil', '']:
                    continue
                
                words.append((
                    word_info.get('word', '').lower(),
                    word_info.get('start', 0) + self.audio_sel[0],
                    word_info.get('end', 0) + self.audio_sel[0]
                ))
            
            logger.info(f"Found {len(words)} aligned words")
            
            # Force direct assignment of timings regardless of word content
            # This is the most reliable approach when word counts match
            words_id = []
            
            if len(words) <= len(self.selected_words):
                # If we have fewer or equal aligned words, assign them in order
                for i, ww in enumerate(self.selected_words):
                    if i < len(words):
                        # Assign timing from aligned word
                        words_id.append((ww[0], ww[1], words[i][1], words[i][2]))
                    else:
                        # No more aligned words available
                        words_id.append((ww[0], ww[1], None, None))
            else:
                # If we have more aligned words than selected words (unusual case)
                # Just use the first N aligned words
                for i, ww in enumerate(self.selected_words):
                    words_id.append((ww[0], ww[1], words[i][1], words[i][2]))
            
            self.all_aligned_words[word_sel[0]:word_sel[1]] = words_id
            return words_id
            
        except Exception as e:
            logger.error(f'MFA alignment failed: {e}')
            import traceback
            logger.error(traceback.format_exc())
            return [(ww[0], ww[1], None, None) for ww in self.selected_words]

    def clean_word(self, w):
        return re.sub(r'[^\w\s]', '', w.lower())  # Strip punctuation

    def write_text_selection(self):
        """Write cleaned full-line transcript to tmp.txt for MFA"""
        # Create mfa_tmp directory if it doesn't exist
        mfa_tmp_dir = self.temp_dir / 'mfa_tmp'
        mfa_tmp_dir.mkdir(exist_ok=True, parents=True)
        
        # Write to mfa_tmp directory instead of temp_dir
        text_path = mfa_tmp_dir / 'tmp.txt'
        cleaned_words = [self.clean_word(item[1]) for item in self.selected_words if item[1].strip()]
        line = ' '.join(cleaned_words)
        with open(text_path, 'w') as f:
            f.write(line + '\n')
        logger.info(f"Writing text selection to {text_path}")
        return text_path
    
    def write_audio_selection(self):
        """Write selected audio to a temporary file (for compatibility with semi_align.py)"""
        logger.info(f"Writing audio selection from {self.audio_sel[0]} to {self.audio_sel[1]}")
        
        # Create mfa_tmp directory if it doesn't exist
        mfa_tmp_dir = self.temp_dir / 'mfa_tmp'
        mfa_tmp_dir.mkdir(exist_ok=True, parents=True)
        
        # Write to mfa_tmp directory instead of temp_dir
        audio_path = mfa_tmp_dir / 'tmp.wav'
        tmp_audio = wave.open(str(audio_path), mode='wb')
        tmp_audio.setparams(self.audio.getparams())
        sr = tmp_audio.getframerate()
        n_frames2write = int((self.audio_sel[1] - self.audio_sel[0]) * sr)
        
        posnow = int(self.audio.tell())
        self.audio.setpos(int(self.audio_sel[0] * sr))
        data = self.audio.readframes(n_frames2write)
        tmp_audio.writeframes(data)
        self.audio.setpos(posnow)
        tmp_audio.close()
        
        logger.info(f"Wrote audio selection to {audio_path}")
        return audio_path

    def __del__(self):
        """Clean up resources when the object is garbage collected"""
        self._cleanup()
    
    def _cleanup(self):
        """
        Clean up temporary resources created during alignment.
        
        This method removes temporary directories created by the aligner
        if they were created by this instance (self._owns_temp_dir is True).
        It also removes the directory from the global cleanup registry.
        
        Exceptions during cleanup are logged but not raised.
        """
        if hasattr(self, '_owns_temp_dir') and self._owns_temp_dir and hasattr(self, 'temp_dir'):
            try:
                # Only clean up if we created the directory
                if self.temp_dir and self.temp_dir.exists():
                    shutil.rmtree(self.temp_dir, ignore_errors=True)
                    logger.info(f"Cleaned up temporary directory: {self.temp_dir}")
                    
                    # Remove from global registry
                    global _temp_dirs_to_cleanup
                    _temp_dirs_to_cleanup.discard(str(self.temp_dir))
            except Exception as e:
                logger.error(f"Error cleaning up temporary directory: {e}")
    
    def _check_models_available(self):
        """Check if models are available and download if needed"""
        try:
            # Check if we're using a pretrained model and if it's available
            if self.use_pretrained_acoustic:
                try:
                    # Check if the model is available
                    models = self.list_available_models()
                    if self.acoustic_model_path not in models["acoustic_models"]:
                        logger.info(f"Acoustic model {self.acoustic_model_path} not found locally, attempting to download...")
                        download_result = subprocess.run(
                            ["mfa", "model", "download", "acoustic", self.acoustic_model_path],
                            capture_output=True,
                            text=True,
                            check=True
                        )
                        logger.info(f"Downloaded acoustic model: {self.acoustic_model_path}")
                except Exception as e:
                    logger.warning(f"Could not check or download acoustic model: {e}")
        except Exception as e:
            logger.error(f"Error checking models: {e}")
    
    def list_available_models(self):
        """List available MFA models
        
        Returns:
            dict: Dictionary of available models
        """
        models = {
            "dictionaries": [],
            "acoustic_models": []
        }
        
        try:
            # Get dictionaries
            result = subprocess.run(
                ["mfa", "model", "list", "dictionary"],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse output - improved parsing
            for line in result.stdout.strip().split('\n'):
                line = line.strip()
                if line and not line.startswith('Available') and not line.startswith('---'):
                    # Clean up any extra characters
                    model_name = line.strip("[]'\" ")
                    if model_name:
                        models["dictionaries"].append(model_name)
            
            # Get acoustic models
            result = subprocess.run(
                ["mfa", "model", "list", "acoustic"],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse output - improved parsing
            raw_output = result.stdout.strip()
            logger.debug(f"Raw acoustic model list: {raw_output}")
            
            # Handle the case where the output might be a single string with the model name
            if "english_us_arpa" in raw_output:
                models["acoustic_models"].append("english_us_arpa")
            else:
                # Otherwise parse line by line
                for line in raw_output.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('Available') and not line.startswith('---'):
                        # Clean up any extra characters
                        model_name = line.strip("[]'\" ")
                        if model_name:
                            models["acoustic_models"].append(model_name)
            
            logger.info(f"Parsed acoustic models: {models['acoustic_models']}")
                    
        except Exception as e:
            logger.error(f"Error listing models: {e}")
        
        return models
    
    def _validate_models(self):
        """Validate that dictionary and acoustic model paths exist
        
        Returns:
            bool: True if models are valid
        
        Raises:
            RuntimeError: If models are not valid
        """
        try:
            # Check if dictionary path exists
            dict_path = Path(self.dictionary_path)
            if not dict_path.exists():
                raise RuntimeError(f"Dictionary file not found: {dict_path}")
            
            # Check if acoustic model exists - either as a path or as a pretrained model
            if self.use_pretrained_acoustic:
                # Check if the pretrained model is available
                models = self.list_available_models()
                logger.info(f"Checking if acoustic model '{self.acoustic_model_path}' is in available models: {models['acoustic_models']}")
                
                if self.acoustic_model_path in models["acoustic_models"]:
                    logger.info(f"Acoustic model '{self.acoustic_model_path}' is already available")
                else:
                    # Only try to download if not already available
                    logger.info(f"Acoustic model '{self.acoustic_model_path}' not found locally, attempting to download...")
                    download_result = subprocess.run(
                        ["mfa", "model", "download", "acoustic", self.acoustic_model_path],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    logger.info(f"Downloaded acoustic model: {self.acoustic_model_path}")
            else:
                # Check if acoustic model path exists as a file
                model_path = Path(self.acoustic_model_path)
                if not model_path.exists():
                    raise RuntimeError(f"Acoustic model not found: {model_path}")
            
            logger.info(f"Using dictionary: {dict_path}")
            logger.info(f"Using acoustic model: {self.acoustic_model_path}")
            
            return True
        except Exception as e:
            logger.error(f"Error validating models: {e}")
            raise RuntimeError(f"Error validating models: {e}")
    
    def _prepare_audio(self, audio_path: Path) -> Path:
        """
        Verify audio file meets requirements for MFA
        
        Args:
            audio_path: Path to audio file
        
        Returns:
            Path: Path to verified audio file
        """
        try:
            # Create mfa_tmp directory instead of corpus
            mfa_tmp_dir = self.temp_dir / "mfa_tmp"
            mfa_tmp_dir.mkdir(exist_ok=True, parents=True)
            
            # Get audio file stem
            audio_stem = Path(audio_path).stem
            
            # Create output path
            output_path = mfa_tmp_dir / f"{audio_stem}.wav"
            
            # Verify audio format
            import soundfile as sf
            data, sample_rate = sf.read(audio_path)
            
            # Verify mono
            if len(data.shape) > 1:
                raise RuntimeError(
                    "Audio must be mono (single channel). Current audio has multiple channels.\n\n"
                    "To convert using Audacity:\n"
                    "1. Open your audio file in Audacity\n"
                    "2. Select the track > Click 'Audio Track Dropdown Menu' > Click 'Split to Mono'\n"
                    "3. Delete one channel\n"
                    "4. Export as WAV: File > Export > Export as WAV"
                )

            # Verify sample rate
            if sample_rate != 16000:
                raise RuntimeError(
                    f"Audio must be 16kHz (current: {sample_rate}Hz).\n\n"
                    "To resample using Audacity:\n"
                    "1. Open your audio file in Audacity\n"
                    "2. Select 'Tracks' menu > 'Resample...' > Select '16000 Hz'\n"
                    "3. Export as WAV: File > Export > Export as WAV"
                )
            
            # Copy WAV file
            import shutil
            shutil.copy(audio_path, output_path)
            logger.info(f"Copied audio to {output_path}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error preparing audio: {e}")
            raise RuntimeError(f"Error preparing audio: {e}")
    
    def _prepare_text(self, text_path: Path) -> Path:
        """
        Prepare text file for MFA
        
        Args:
            text_path: Path to text file
            
        Returns:
            Path: Path to prepared text file
        """
        # Simply return the original text path - no need to create a .lab file
        return text_path
    
    def align(self, audio_path: Path, text_path: Path, 
              progress_callback: Callable[[float, str], None] = None,
              timeout: int = 1800) -> Dict:
        """
        Run alignment on audio and text files with timeout
        
        Args:
            audio_path: Path to audio file
            text_path: Path to text file
            progress_callback: Callback function for progress updates
            timeout: Maximum time in seconds to wait for alignment (default: 30 minutes)
            
        Returns:
            Dictionary with alignment results
        """
        try:
            # Update progress
            if progress_callback:
                progress_callback(0.05, "Validating models...")
            
            # Validate models
            self._validate_models()
            
            # Update progress
            if progress_callback:
                progress_callback(0.1, "Preparing files...")
            
            # Clean up existing directories and files
            mfa_tmp_dir = self.temp_dir / "mfa_tmp"
            output_dir = self.temp_dir / "aligned"
            
            # Remove existing directories to ensure clean state
            for dir_path in [output_dir]:
                if dir_path.exists():
                    shutil.rmtree(dir_path)
                dir_path.mkdir(exist_ok=True, parents=True)
            
            # Make sure mfa_tmp directory exists
            mfa_tmp_dir.mkdir(exist_ok=True, parents=True)
            
            # Copy audio file to mfa_tmp directory
            audio_filename = "tmp.wav"
            target_audio_path = mfa_tmp_dir / audio_filename
            shutil.copy(audio_path, target_audio_path)
            
            # Copy text content to a text file with same name but .txt extension
            text_filename = "tmp.txt"
            target_text_path = mfa_tmp_dir / text_filename
            with open(text_path, 'r', encoding='utf-8') as src:
                text_content = src.read().replace('\n', ' ').strip()
            with open(target_text_path, 'w', encoding='utf-8') as dst:
                dst.write(text_content)
            
            logger.info(f"Prepared audio: {target_audio_path}")
            logger.info(f"Prepared text: {target_text_path}")
            
            # Update progress
            if progress_callback:
                progress_callback(0.2, "Starting alignment...")
            
            # Run MFA alignment with timeout and --clean flag
            cmd = [
                "mfa",
                "align",
                "--clean",  # Force clean previous alignments
                str(mfa_tmp_dir),  # Directory containing audio and text files
                str(self.dictionary_path),
            ]

            # Add the acoustic model - either as a name or path
            if self.use_pretrained_acoustic:
                cmd.append(self.acoustic_model_path)
            else:
                cmd.append(str(self.acoustic_model_path))

            # Add the output directory
            cmd.append(str(output_dir))

            logger.info(f"Running command: {' '.join(cmd)}")
            
            # Use shell=True on Windows to find commands in PATH
            shell = sys.platform == 'win32'
            
            # Start process with timeout
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=shell,
                bufsize=1  # Line buffered
            )
            
            # Wait for process to complete with timeout
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                
                # Log output
                if stdout:
                    logger.info(f"MFA stdout: {stdout}")
                if stderr:
                    logger.warning(f"MFA stderr: {stderr}")
                    
                # Check return code
                if process.returncode != 0:
                    raise RuntimeError(f"MFA alignment failed with return code {process.returncode}")
                    
            except subprocess.TimeoutExpired:
                # Kill process if it times out
                process.kill()
                raise RuntimeError(f"MFA alignment timed out after {timeout} seconds")
            
            # Update progress
            if progress_callback:
                progress_callback(0.8, "Processing results...")
            
            # Find TextGrid file
            textgrid_files = list(output_dir.glob("**/*.TextGrid"))
            if not textgrid_files:
                raise RuntimeError("No TextGrid files found in output directory")
            
            # Parse TextGrid file
            alignment_results = self._parse_textgrid(textgrid_files[0])
            
            # Update progress
            if progress_callback:
                progress_callback(1.0, "Alignment complete")
            
            return alignment_results
        
        except Exception as e:
            logger.error(f"Error running alignment: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise RuntimeError(f"Error running alignment: {e}")
    
    def _parse_textgrid(self, textgrid_path):
        """Parse TextGrid file using a similar approach to the original SegmentAligner
        
        Args:
            textgrid_path: Path to TextGrid file
        
        Returns:
            Dictionary with alignment results
        """
        try:
            # Import textgrid module from the same location as the original code
            from textgrid_remote.textgrid import textgrid
            
            logger.info(f"Parsing TextGrid file: {textgrid_path}")
            
            # Create TextGrid object and read file
            grid = textgrid.TextGrid()
            grid.read(str(textgrid_path))
            
            # Extract word information similar to the original implementation
            s_word_strings = []
            for ww in self.selected_words:
                s_word_strings.append(ww[1].lower())
            
            result = {
                "words": [],
                "duration": grid.maxTime  # Changed from grid.maxTime() to grid.maxTime
            }
            
            # Get word tier
            tiers = grid.getList('words')
            if not tiers:
                logger.error("No word tier found in TextGrid")
                raise RuntimeError("No word tier found in TextGrid")
            
            # Process intervals similar to the original implementation
            for tier in tiers:
                for interval in tier.intervals:
                    # Only include non-empty intervals
                    if interval.mark and interval.mark.strip():
                        word_info = {
                            "word": interval.mark.lower(),
                            "start": interval.minTime,
                            "end": interval.maxTime
                        }
                        result["words"].append(word_info)
            
            logger.info(f"Extracted {len(result['words'])} words from TextGrid")
            return result
        
        except Exception as e:
            logger.error(f"Error parsing TextGrid: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise RuntimeError(f"Error parsing TextGrid: {e}")
    
    def export(self, file_path, alignment_results, format_type="textgrid"):
        """Export alignment results to file
        
        Args:
            file_path: Path to output file
            alignment_results: Alignment results dictionary
            format_type: Output format (textgrid, json, csv)
        """
        try:
            format_type = format_type.lower()
            
            if format_type == "textgrid":
                self._export_textgrid(file_path, alignment_results)
            elif format_type == "json":
                self._export_json(file_path, alignment_results)
            elif format_type == "csv":
                self._export_csv(file_path, alignment_results)
            else:
                raise ValueError(f"Unsupported export format: {format_type}")
                
            logger.info(f"Exported alignment results to {file_path}")
            
        except Exception as e:
            logger.error(f"Error exporting alignment results: {e}")
            raise RuntimeError(f"Error exporting alignment results: {e}")
    
    def _export_textgrid(self, file_path, alignment_results):
        """Export alignment results as TextGrid
        
        Args:
            file_path: Path to output file
            alignment_results: Alignment results dictionary
        """
        try:
            # Import textgrid module
            import textgrid
            
            # Create TextGrid
            tg = textgrid.TextGrid()
            
            # Add word tier
            word_tier = textgrid.IntervalTier(name="words")
            word_tier.maxTime = alignment_results.get("duration", 0)
            
            # Add words
            for word in alignment_results["words"]:
                if word["word"] and word["word"] != "sp":  # Skip silence
                    word_tier.addInterval(
                        textgrid.Interval(
                            word["start"],
                            word["end"],
                            word["word"]
                        )
                    )
            
            tg.append(word_tier)
            
            # Add phone tier if available
            has_phones = any("phones" in word for word in alignment_results["words"])
            if has_phones:
                phone_tier = textgrid.IntervalTier(name="phones")
                phone_tier.maxTime = alignment_results.get("duration", 0)
                
                # Add phones
                for word in alignment_results["words"]:
                    if "phones" in word and word["phones"]:
                        for phone in word["phones"]:
                            phone_tier.addInterval(
                                textgrid.Interval(
                                    phone["start"],
                                    phone["end"],
                                    phone["phone"]
                                )
                            )
                
                tg.append(phone_tier)
            
            # Write TextGrid to file
            tg.write(file_path)
            
        except Exception as e:
            logger.error(f"Error exporting TextGrid: {e}")
            raise RuntimeError(f"Error exporting TextGrid: {e}")
    
    def _export_json(self, file_path, alignment_results):
        """Export alignment results as JSON
        
        Args:
            file_path: Path to output file
            alignment_results: Alignment results dictionary
        """
        try:
            # Create output data
            output_data = {
                "duration": alignment_results.get("duration", 0),
                "words": []
            }
            
            # Add words
            for word in alignment_results["words"]:
                word_data = {
                    "word": word["word"],
                    "start": word["start"],
                    "end": word["end"]
                }
                
                # Add phones if available
                if "phones" in word and word["phones"]:
                    word_data["phones"] = word["phones"]
                
                output_data["words"].append(word_data)
            
            # Write JSON to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2)
            
        except Exception as e:
            logger.error(f"Error exporting JSON: {e}")
            raise RuntimeError(f"Error exporting JSON: {e}")
    
    def _export_csv(self, file_path, alignment_results):
        """Export alignment results as CSV
        
        Args:
            file_path: Path to output file
            alignment_results: Alignment results dictionary
        """
        try:
            # Create CSV file
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Write header
                writer.writerow(["word", "start", "end", "phones"])
                
                # Write words
                for word in alignment_results["words"]:
                    if word["word"] and word["word"] != "sp":  # Skip silence
                        # Format phones if available
                        phones = ""
                        if "phones" in word and word["phones"]:
                            phones = " ".join([f"{p['phone']}:{p['start']:.3f}-{p['end']:.3f}" for p in word["phones"]])
                        
                        # Write row
                        writer.writerow([
                            word["word"],
                            f"{word['start']:.3f}",
                            f"{word['end']:.3f}",
                            phones
                        ])
            
        except Exception as e:
            logger.error(f"Error exporting CSV: {e}")
            raise RuntimeError(f"Error exporting CSV: {e}")

class SegmentAligner:
    """Wrapper for Montreal Forced Aligner compatible with semi_align.py"""
    
    def clean_word(self, w):
        return re.sub(r'[^\w\s]', '', w.lower())  # Strip punctuation
    
    def __init__(self, audiofile, textfile, temp_path, dictionary_path=None, 
                 acoustic_model_path=None, use_pretrained_acoustic=None):
        """Initialize the aligner
        
        Args:
            audiofile: Path to audio file
            textfile: Path to text file
            temp_path: Path to use as temporary directory
            dictionary_path: Path to dictionary file (optional)
            acoustic_model_path: Path or name of acoustic model (optional)
            use_pretrained_acoustic: Whether to use a pretrained model (optional)
        """
        # Store temp directory
        self.temp_path = temp_path
        if not os.path.exists(temp_path):
            os.makedirs(temp_path, exist_ok=True)
        
        # Open audio file
        self.audio = wave.open(audiofile, mode='rb')
        
        # Read text file
        with open(textfile, 'r') as texthandle:
            text = texthandle.read()
        
        # Split text into words
        all_words = text.split()
        self.all_aligned_words = []
        tmpid = 0
        
        # Initialize all aligned words with None 
        for ww in all_words:
            idstring = "w" + str(tmpid)
            self.all_aligned_words.append((idstring, ww.lower(), None, None))
            tmpid += 1
        
        self.audio_sel = (0, -1)
        self.aligned_words = []
        self.selected_words = []
        
        # Initialize MFA wrapper with optional model paths
        self.mfa = MFAWrapper(
            temp_path=temp_path,
            dictionary_path=dictionary_path,
            acoustic_model_path=acoustic_model_path,
            use_pretrained_acoustic=use_pretrained_acoustic
        )
    
    def align_all(self):
        """Align all words in the text"""
        self.align_segment((0, -1), (0, None))
    
    def align_segment(self, audio_sel, word_sel):
        """Align a segment of audio to a selection of words
        
        Args:
            audio_sel: Tuple of (start_time, end_time) in seconds
            word_sel: Tuple of (start_index, end_index) in words list
            
        Returns:
            List of aligned words with timing information
        """
        self.audio_sel = audio_sel
        self.selected_words = self.all_aligned_words[word_sel[0]:word_sel[1]]
        
        # Write temporary files
        audio_path = self.write_audio_selection()
        text_path = self.write_text_selection()
        
        # Run alignment
        try:
            # Run MFA alignment
            alignment_results = self.mfa.align(audio_path, text_path)
            
            # Convert MFA results to the format expected by semi_align.py
            # This format is (word, start_time, end_time) without the ID
            words = []
            for word_info in alignment_results.get('words', []):
                # Skip silence markers
                if word_info.get('word', '').lower() in ['sp', 'sil', '']:
                    continue
                    
                words.append((
                    word_info.get('word', '').lower(),
                    word_info.get('start', 0) + self.audio_sel[0],
                    word_info.get('end', 0) + self.audio_sel[0]
                ))
            
            logger.info(f"Found {len(words)} aligned words")
            self.aligned_words = words
            
            # Update word timings in all_aligned_words
            words_id = []
            i = 0
            for ww in self.all_aligned_words[word_sel[0]:word_sel[1]]:
                # Clean the word before comparison
                clean_original = self.clean_word(ww[1])
                if i >= len(words) or not clean_original == words[i][0].lower():
                    logger.warning(f'Word "{ww[1]}" has not been aligned... skipping')
                    words_id.append((ww[0], ww[1], None, None))
                else:
                    words_id.append((ww[0], ww[1], words[i][1], words[i][2]))
                    i += 1
            
            self.all_aligned_words[word_sel[0]:word_sel[1]] = words_id
            return words_id
            
        except Exception as e:
            logger.error(f'MFA alignment failed: {e}')
            import traceback
            logger.error(traceback.format_exc())
            return [(ww[0], ww[1], None, None) for ww in self.selected_words]
    
    def write_text_selection(self):
        """Write selected text to a temporary file"""
        text_path = Path(self.temp_path) / 'tmp.txt'
        with open(text_path, 'w') as f:
            cleaned_words = [self.clean_word(item[1]) for item in self.selected_words if item[1].strip()]
            text = ' '.join(cleaned_words)
            f.write(text)
        
        logger.info(f"Writing text selection to {text_path}")
        return text_path

    def write_audio_selection(self):
        """Write selected audio to a temporary file (for compatibility with semi_align.py)"""
        start_sec = self.audio_sel[0]
        end_sec = self.audio_sel[1]
        logger.info(f"Writing audio selection from {start_sec:.3f}s to {end_sec:.3f}s")

        audio_path = Path(self.temp_path) / 'tmp.wav'
        tmp_audio = wave.open(str(audio_path), mode='wb')
        tmp_audio.setparams(self.audio.getparams())

        sr = tmp_audio.getframerate()
        max_frames = self.audio.getnframes()

        start_frame = round(start_sec * sr)
        end_frame = round(end_sec * sr)

        # Clamp frame indices to valid range
        start_frame = max(0, min(start_frame, max_frames))
        end_frame = max(0, min(end_frame, max_frames))
        n_frames2write = end_frame - start_frame

        # Read and write the correct portion of the audio
        posnow = self.audio.tell()
        self.audio.setpos(start_frame)
        data = self.audio.readframes(n_frames2write)
        tmp_audio.writeframes(data)
        self.audio.setpos(posnow)
        tmp_audio.close()
        
        return audio_path


