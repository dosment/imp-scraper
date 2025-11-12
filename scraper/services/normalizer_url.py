"""
URL normalization service.
Implements the normalization rules from original_prompt.md.
"""

from typing import Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from ..utils import URLValidator


class URLNormalizer:
    """
    Normalize URLs according to specifications:
    - Force HTTPS
    - Remove tracking parameters
    - Keep trailing slash if present
    """

    # Tracking parameters to remove (per original_prompt.md)
    TRACKING_PARAMS = {
        'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
        'gclid', 'fbclid', 'mc_cid', 'mc_eid', '_ga', '_gl', '_gac',
        'msclkid', 'twclid', '_kx'
    }

    @staticmethod
    def normalize(url: str, force_https: bool = True, remove_tracking: bool = True) -> str:
        """
        Normalize a URL.

        Args:
            url: URL to normalize
            force_https: Force HTTPS scheme (default: True)
            remove_tracking: Remove tracking parameters (default: True)

        Returns:
            Normalized URL string
        """
        if not url:
            return url

        try:
            parsed = urlparse(url)

            # Force HTTPS if requested
            scheme = 'https' if force_https else parsed.scheme
            if not scheme:
                scheme = 'https'

            # Remove tracking parameters if requested
            if remove_tracking:
                query_params = parse_qs(parsed.query)
                clean_params = {
                    k: v for k, v in query_params.items()
                    if k not in URLNormalizer.TRACKING_PARAMS
                }
                query = urlencode(clean_params, doseq=True) if clean_params else ''
            else:
                query = parsed.query

            # Keep path structure
            path = parsed.path if parsed.path else '/'

            # Rebuild URL
            normalized = urlunparse((
                scheme,
                parsed.netloc,
                path,
                parsed.params,
                query,
                ''  # Remove fragment
            ))

            return normalized

        except Exception:
            # If parsing fails, return original URL
            return url

    @staticmethod
    def normalize_dealer_url(url: str) -> str:
        """
        Normalize a dealer website URL.
        Ensures it's a valid root URL with trailing slash.
        """
        normalized = URLNormalizer.normalize(url)

        # Ensure trailing slash for root URLs
        parsed = urlparse(normalized)
        if not parsed.path or parsed.path == '/':
            if not normalized.endswith('/'):
                normalized += '/'

        return normalized

    @staticmethod
    def is_dealer_domain(url: str, dealer_url: str) -> bool:
        """
        Check if a URL belongs to the dealer's domain.
        Used to verify service scheduler and credit app URLs.
        """
        return URLValidator.is_same_domain(url, dealer_url)

    @staticmethod
    def clean_facebook_url(url: str) -> str:
        """
        Clean and normalize a Facebook URL.
        Removes tracking parameters and ensures standard format.
        """
        if not url or 'facebook.com' not in url.lower():
            return url

        normalized = URLNormalizer.normalize(url)

        # Remove common Facebook-specific parameters
        fb_params = {'ref', 'fref', 'hc_location', '__tn__', '__cft__'}

        try:
            parsed = urlparse(normalized)
            query_params = parse_qs(parsed.query)
            clean_params = {
                k: v for k, v in query_params.items()
                if k not in fb_params and k not in URLNormalizer.TRACKING_PARAMS
            }

            query = urlencode(clean_params, doseq=True) if clean_params else ''

            # Remove trailing slash for Facebook URLs (they don't use them)
            path = parsed.path.rstrip('/')

            return urlunparse((
                parsed.scheme,
                parsed.netloc,
                path,
                '',
                query,
                ''
            ))

        except Exception:
            return normalized

    @staticmethod
    def clean_google_maps_url(url: str) -> str:
        """
        Clean and normalize a Google Maps URL.
        Preserves the essential place ID or coordinates.
        """
        if not url or 'google.com/maps' not in url.lower() and 'maps.google.com' not in url.lower():
            return url

        # Google Maps URLs can be complex; just remove tracking params
        try:
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)

            # Keep important params (cid, place_id, q)
            important_params = {'cid', 'place_id', 'q', 'll', 'z'}
            clean_params = {
                k: v for k, v in query_params.items()
                if k in important_params or k not in URLNormalizer.TRACKING_PARAMS
            }

            query = urlencode(clean_params, doseq=True) if clean_params else ''

            return urlunparse((
                'https',  # Always HTTPS for Google
                parsed.netloc,
                parsed.path,
                parsed.params,
                query,
                ''
            ))

        except Exception:
            return url
