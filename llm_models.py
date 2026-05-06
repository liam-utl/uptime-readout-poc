# Each entry: (model_id, use_params)
# use_params=True  → pass temperature=0 and response_format to LiteLLM
# use_params=False → bare completion call, no extra params

OPENAI_MODELS: list[tuple[str, bool]] = [
    ("gpt-5.2",      True),
    ("gpt-4.1",      True),
    ("gpt-4.1-mini", True),
    ("gpt-4.1-nano", True),
    ("gpt-4o",       True),
    ("gpt-4o-mini",  True),
]

BEDROCK_MODELS: list[tuple[str, bool]] = [
    ("arn:aws:bedrock:eu-west-1:428265895497:inference-profile/eu.anthropic.claude-haiku-4-5-20251001-v1:0",  False),
    ("arn:aws:bedrock:eu-west-1:428265895497:inference-profile/eu.anthropic.claude-opus-4-5-20251101-v1:0",   True),
    ("arn:aws:bedrock:eu-west-1:428265895497:inference-profile/eu.anthropic.claude-opus-4-6-v1",              False),
    ("arn:aws:bedrock:eu-west-1:428265895497:inference-profile/eu.anthropic.claude-opus-4-7",                 True),
    ("arn:aws:bedrock:eu-west-1:428265895497:inference-profile/eu.anthropic.claude-sonnet-4-5-20250929-v1:0", False),
    ("arn:aws:bedrock:eu-west-1:428265895497:inference-profile/eu.anthropic.claude-sonnet-4-6",               False),
    ("arn:aws:bedrock:eu-west-1::foundation-model/google.gemma-3-4b-it",                                      True),
    ("arn:aws:bedrock:eu-west-1::foundation-model/nvidia.nemotron-nano-12b-v2",                               True),
    ("arn:aws:bedrock:eu-west-1:428265895497:inference-profile/eu.amazon.nova-2-lite-v1:0",                   True),
    ("arn:aws:bedrock:eu-west-1:428265895497:inference-profile/eu.anthropic.claude-3-haiku-20240307-v1:0",    True),
    ("arn:aws:bedrock:eu-west-1:428265895497:inference-profile/eu.anthropic.claude-opus-4-5-20251101-v1:0",   True),
    ("arn:aws:bedrock:eu-west-1::foundation-model/openai.gpt-oss-safeguard-120b",                             True),
    ("arn:aws:bedrock:eu-west-1::foundation-model/google.gemma-3-27b-it",                                     True),
    ("arn:aws:bedrock:eu-west-1::foundation-model/openai.gpt-oss-120b-1:0",                                   True),
]

#     "arn:aws:bedrock:eu-west-1:428265895497:inference-profile/eu.anthropic.claude-sonnet-4-20250514-v1:0",
#     "arn:aws:bedrock:eu-west-1:428265895497:inference-profile/eu.anthropic.claude-3-sonnet-20240229-v1:0",
