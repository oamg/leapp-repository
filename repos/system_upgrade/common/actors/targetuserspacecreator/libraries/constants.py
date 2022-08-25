import os

SCRATCH_DIR = os.getenv('LEAPP_CONTAINER_ROOT', '/var/lib/leapp/scratch')
MOUNTS_DIR = os.path.join(SCRATCH_DIR, 'mounts')
TARGET_USERSPACE = '/var/lib/leapp/el{}userspace'
PROD_CERTS_FOLDER = 'prod-certs'
PERSISTENT_PACKAGE_CACHE_DIR = '/var/lib/leapp/persistent_package_cache'
