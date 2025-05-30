# Using Montreal Forced Aligner with semi_automatic_aligner

This guide explains how to set up and use the Montreal Forced Aligner (MFA) with the semi_automatic_aligner GUI.

## Installation

### Prerequisites
- [x] Install anaconda or miniconda
- [x] Install MFA using conda:
  ```
  conda create -n aligner -c conda-forge montreal-forced-aligner
  conda activate aligner
  ```

### Setting up MFA

1. Download the required models:
   ```
   mfa model download acoustic english_us_arpa
   mfa model download dictionary english_us_arpa
   ```

2. Configure the dictionary and acoustic model paths:
   
   The aligner looks for a configuration file in the following locations:
   - `~/.mfa_config.json` (in your home directory)
   - `mfa_config.json` (in the current directory)
   
   Create one of these files with the following content:
   ```json
   {
     "dictionary_path": "~/Documents/MFA/pretrained_models/dictionary/english_us_arpa.dict",
     "acoustic_model_path": "english_us_arpa",
     "use_pretrained_acoustic": true
   }
   ```

   If you're using the pretrained models from MFA, you can set `use_pretrained_acoustic` to `true` and specify just the model name for `acoustic_model_path`. The aligner will automatically download the model if it's not found.

   If you have your own dictionary file, set the full path in `dictionary_path`. Make sure to expand the `~` to your home directory or use an absolute path.

### Troubleshooting dictionary and acoustic model issues

If the aligner can't find your dictionary or acoustic model:

- For dictionary issues:
  - Make sure the path in your config file is correct
  - You can find where MFA stores dictionaries by running: `mfa model list dictionary`
  - Copy the dictionary file to the path specified in your config

- For acoustic model issues:
  - If using pretrained models, ensure you've downloaded them with `mfa model download acoustic english_us_arpa`
  - You can list available acoustic models with: `mfa model list acoustic`
  - If you need to use a different model, update your config file accordingly

## Using MFA with semi_automatic_aligner

1. Clone the repository:
   ```
   git clone --recurse-submodules -j8 https://github.com/s-michelmann/semi_automatic_aligner
   ```

2. Install requirements:
   ```
   cd semi_automatic_aligner
   conda activate aligner
   conda install --file requirements.txt
   ```

3. Run the GUI:
   ```
   python semi_align.py
   ```

4. When using the GUI:
   - Open a .wav file and a .txt file containing the transcription
   - The GUI will use MFA for alignment if it's properly configured
   - Note that .wav files should be mono channel and sampled at 16kHz for best results with MFA

## Audio Format Requirements

MFA has specific requirements for audio files:
- Must be mono (single channel)
- Should be sampled at 16kHz

If your audio doesn't meet these requirements, you can convert it using tools like Audacity:
1. Open your audio file in Audacity
2. For stereo files: Tracks > Mix > Mix Stereo Down to Mono
3. For sample rate: Tracks > Resample > 16000 Hz
4. Export as WAV: File > Export > Export as WAV