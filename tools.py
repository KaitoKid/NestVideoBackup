import logging
import re


class TokenRedactFilter(logging.Filter):
    """Redact Google master tokens and access tokens from log output."""
    PATTERNS = [
        (re.compile(r'aas_et[^\s"\']{10,}'), '[REDACTED_MASTER_TOKEN]'),
        (re.compile(r'ya29\.[^\s"\']+'), '[REDACTED_ACCESS_TOKEN]'),
    ]

    def filter(self, record):
        if isinstance(record.msg, str):
            for pattern, replacement in self.PATTERNS:
                record.msg = pattern.sub(replacement, record.msg)
        if record.args:
            new_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    for pattern, replacement in self.PATTERNS:
                        arg = pattern.sub(replacement, arg)
                new_args.append(arg)
            record.args = tuple(new_args)
        return True


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.addFilter(TokenRedactFilter())

# Also add the filter to the root logger so all loggers benefit
logging.getLogger().addFilter(TokenRedactFilter())
