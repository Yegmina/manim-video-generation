# Customizable Auto Mode for Video Generation

## Overview

The customizable auto mode feature allows users to fine-tune the video generation process by configuring various parameters such as retry attempts, model selection, and error handling strategies. This feature maintains backward compatibility while providing advanced customization options.

## API Endpoint

**Endpoint:** `POST /api/v1/text2video/auto`

**Base URL:** `http://localhost:8000/api/v1/text2video/auto`

## Request Parameters

### Required Parameters

- `prompt` (string): Natural language description of the desired video
- `quality` (VideoQuality): Video quality setting (LOW_QUALITY, MEDIUM_QUALITY, HIGH_QUALITY)
- `format` (VideoFormat): Output video format (MP4, AVI, MOV)

### Optional Parameters

- `auto_config` (AutoModeConfig): Configuration object for customizing auto mode behavior

## AutoModeConfig Parameters

### Core Configuration

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `max_total_attempts` | int | 15 | 1-50 | Maximum total attempts across all phases |
| `max_llm_attempts_per_phase` | int | 3 | 1-10 | Maximum LLM attempts per phase |
| `enable_prompt_rewriting` | bool | true | - | Enable prompt rewriting phase |
| `enable_prompt_simplification` | bool | true | - | Enable prompt simplification phase |
| `enable_gemini_fallback` | bool | true | - | Enable Gemini model fallback |
| `enable_video_error_feedback` | bool | true | - | Enable video error feedback for retries |
| `preferred_models` | List[str] | ["gemma-3-27b-it", "gemini-2.5-flash-lite", "gemini-2.5-flash"] | - | Preferred models in order of preference |
| `custom_prompt_modifiers` | List[str] | [] | - | Custom prompt modifiers to apply |

## Usage Examples

### 1. Default Auto Mode (Backward Compatible)

```python
import requests

url = "http://localhost:8000/api/v1/text2video/auto"
data = {
    "prompt": "Create a simple animation showing a bouncing ball",
    "quality": "LOW_QUALITY",
    "format": "MP4"
}

response = requests.post(url, json=data)
print(response.json())
```

### 2. High-Quality Customized Auto Mode

```python
data = {
    "prompt": "Create a complex mathematical animation showing the Pythagorean theorem",
    "quality": "HIGH_QUALITY",
    "format": "MP4",
    "auto_config": {
        "max_total_attempts": 20,
        "max_llm_attempts_per_phase": 5,
        "enable_prompt_rewriting": True,
        "enable_prompt_simplification": True,
        "enable_gemini_fallback": True,
        "enable_video_error_feedback": True,
        "preferred_models": ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemma-3-27b-it"],
        "custom_prompt_modifiers": [
            "Use clear mathematical notation",
            "Include step-by-step explanations",
            "Make the animation educational and engaging"
        ]
    }
}
```

### 3. Fast Auto Mode (Optimized for Speed)

```python
data = {
    "prompt": "Create a quick text animation",
    "quality": "LOW_QUALITY",
    "format": "MP4",
    "auto_config": {
        "max_total_attempts": 8,
        "max_llm_attempts_per_phase": 2,
        "enable_prompt_rewriting": True,
        "enable_prompt_simplification": True,
        "enable_gemini_fallback": True,
        "enable_video_error_feedback": True,
        "preferred_models": ["gemini-2.5-flash-lite", "gemini-2.5-flash"],
        "custom_prompt_modifiers": [
            "Keep it simple and fast",
            "Use basic animations only"
        ]
    }
}
```

### 4. Minimal Auto Mode (Reduced Attempts)

```python
data = {
    "prompt": "Show a simple circle animation",
    "quality": "LOW_QUALITY",
    "format": "MP4",
    "auto_config": {
        "max_total_attempts": 5,
        "max_llm_attempts_per_phase": 2,
        "enable_prompt_rewriting": False,
        "enable_prompt_simplification": False,
        "enable_gemini_fallback": False,
        "enable_video_error_feedback": False,
        "preferred_models": ["gemini-2.5-flash"],
        "custom_prompt_modifiers": []
    }
}
```

## Auto Mode Phases

The customizable auto mode operates through several phases:

### Phase 1: Primary Model with Error Correction
- Uses the first model in `preferred_models`
- Applies `max_llm_attempts_per_phase` attempts
- Incorporates video error feedback if enabled

### Phase 2: Prompt Rewriting (if enabled)
- Rewrites the original prompt for better clarity
- Uses the primary model with error correction
- Applies `max_llm_attempts_per_phase` attempts

### Phase 3: Prompt Simplification (if enabled)
- Simplifies the original prompt for easier processing
- Uses the primary model with error correction
- Applies `max_llm_attempts_per_phase` attempts

### Phase 4: Secondary Models (if enabled)
- Iterates through remaining models in `preferred_models`
- Each model gets `max_llm_attempts_per_phase` attempts
- Uses video error feedback if enabled

### Final Phase: Simplified Prompt with Fallback
- Combines prompt simplification with the last preferred model
- Uses video error feedback if enabled
- Single attempt with enhanced prompt

## Response Format

```json
{
    "id": 123,
    "title": "Create a simple animation showing a bouncing ball",
    "status": "pending",
    "progress": 0,
    "created_at": "2025-01-27T10:30:00.000000",
    "started_at": null,
    "completed_at": null,
    "processing_time": null,
    "error_message": null,
    "output_file_path": null,
    "file_size": null,
    "duration": null,
    "metadata": {
        "model": "auto",
        "attempt": 1,
        "auto_config": {
            "max_total_attempts": 15,
            "max_llm_attempts_per_phase": 3,
            "enable_prompt_rewriting": true,
            "enable_prompt_simplification": true,
            "enable_gemini_fallback": true,
            "enable_video_error_feedback": true,
            "preferred_models": ["gemma-3-27b-it", "gemini-2.5-flash-lite", "gemini-2.5-flash"],
            "custom_prompt_modifiers": []
        }
    }
}
```

## Error Handling

The API returns appropriate HTTP status codes:

- `201 Created`: Video generation request created successfully
- `400 Bad Request`: Invalid parameters or configuration
- `500 Internal Server Error`: Server-side error during processing

## Best Practices

### 1. Model Selection
- Use faster models (gemini-2.5-flash-lite) for simple animations
- Use more capable models (gemini-2.5-flash) for complex animations
- Consider cost and speed trade-offs when selecting models

### 2. Retry Configuration
- Higher `max_total_attempts` increases success rate but takes longer
- Higher `max_llm_attempts_per_phase` improves quality but increases latency
- Balance between success rate and processing time

### 3. Prompt Modifiers
- Use specific, actionable modifiers
- Keep modifiers concise and clear
- Test different modifier combinations for optimal results

### 4. Error Feedback
- Enable `enable_video_error_feedback` for better error recovery
- Monitor error patterns to adjust configuration
- Use custom prompt modifiers to address common issues

## Testing

Use the provided test script to verify functionality:

```bash
cd fast_backend
python test_customizable_auto.py
```

This script tests various configurations including:
- Default auto mode (backward compatibility)
- Customized auto mode with high-quality settings
- Minimal auto mode with reduced attempts
- Fast auto mode optimized for speed

## Monitoring and Debugging

### Logs
Check the application logs for detailed information about:
- Phase transitions
- Model selection
- Error handling
- Success/failure rates

### Status Checking
Monitor video generation progress:

```python
import requests

def check_status(video_id):
    url = f"http://localhost:8000/api/v1/manim2video/{video_id}/status"
    response = requests.get(url)
    return response.json()

# Check status
status = check_status(123)
print(f"Status: {status['status']}")
print(f"Progress: {status['progress']}%")
```

## Migration from Legacy Auto Mode

The new customizable auto mode is fully backward compatible. Existing code will continue to work without modification. To take advantage of new features, simply add the `auto_config` parameter to your requests.

## Performance Considerations

- **Speed vs Quality**: Lower attempt counts for faster processing, higher counts for better quality
- **Model Costs**: Different models have varying costs and capabilities
- **Resource Usage**: More attempts consume more computational resources
- **Error Recovery**: Video error feedback improves success rates but adds processing time

## Troubleshooting

### Common Issues

1. **High Failure Rate**: Increase `max_total_attempts` and `max_llm_attempts_per_phase`
2. **Slow Processing**: Reduce attempt counts and use faster models
3. **Poor Quality**: Enable prompt rewriting and simplification
4. **Cost Concerns**: Use fewer attempts and cheaper models

### Debugging Tips

1. Check application logs for detailed error information
2. Monitor video generation status for progress updates
3. Test with minimal configuration to isolate issues
4. Use custom prompt modifiers to address specific problems

## Future Enhancements

Planned improvements include:
- Dynamic configuration based on prompt complexity
- A/B testing capabilities for configuration optimization
- Machine learning-based parameter tuning
- Real-time configuration adjustment based on success rates
