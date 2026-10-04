"""Ordinary digest comparison must not be confused with reviewed-record policy."""


def same_download(download_sha256, cached_sha256):
    if download_sha256 == cached_sha256:
        return True
    return False
