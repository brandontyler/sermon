# PSR Proof of Concepts

## POC Summary

| POC | Script | What It Proves |
|-----|--------|---------------|
| #1 | `psr_poc.py` | End-to-end: Whisper + GPT-4o → delivery score |
| #2 | `scripture_analyzer.py` | Scripture detection + verification with free APIs |
| #3 | `audio_analysis_poc.py` | Parselmouth audio metrics + Whisper on real Piper sermon |
| #4 | `sermon_comparison.py` | Cross-sermon comparison, sermon type bias confirmed |
| #5 | `azure_multipass_poc.py` | Full Azure multi-model pipeline (3 parallel passes) |
| #6 | `azure_fast_transcription_poc.py` | Fast transcription API — fixes POC #5 word loss |
| #7 | `validated_multipass_poc.py` | Re-scores POC #5 on full transcript — validates scoring accuracy |

## Key Decisions from POCs

- **Parselmouth only** open-source tool in MVP (textstat/spaCy dropped — POC #4)
- **LLM for all text analysis** — strictly better than NLP heuristics (POC #4)
- **Azure AI Speech fast transcription API** for production — synchronous, no blob storage, 47x faster than real-time, 99.2% word recovery (POC #6)
- **Multi-model strategy** — o4-mini for biblical, GPT-4.1 for structure, GPT-4.1-mini for delivery (POC #5)
- **Normalize by sermon type** — 3-4x scripture density gap between expository and topical (POC #4)
- **Full transcript matters** — scoring on partial transcript (28%) underestimated composite by 5.3 points. Application +13, Clarity +10, Delivery +10 with complete text (POC #7)

## Running POC #5 (Latest)

```bash
source .venv/bin/activate
python poc/azure_multipass_poc.py poc/samples/piper_called_according_to_his_purpose.mp3
python poc/azure_multipass_poc.py poc/samples/piper_called_according_to_his_purpose.mp3 --skip-transcribe  # reuse cached transcript
```

Requires Azure CLI logged in with access to `rg-sermon-rating-dev` resource group.
