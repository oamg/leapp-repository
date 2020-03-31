#!/bin/bash

# Decrypt private SSH key
ENCRYPTED_FILE=.travis/githubio-data-idrsa
DECRYPTED_FILE=${ENCRYPTED_FILE}-dec
openssl aes-256-cbc -K $aes_encryption_key -iv $aes_encryption_iv -in $ENCRYPTED_FILE -out $DECRYPTED_FILE -d

# Setup SSH agent with decrypted private SSH key
eval "$(ssh-agent -s)"
chmod 0600 $DECRYPTED_FILE
ssh-add $DECRYPTED_FILE

# Clone githubio-data repository
git clone --depth 1 --branch master git@github.com:oamg/githubio-data

cd githubio-data
# Setting username and email for committer
git config user.name "Leapp Build Automation"
git config user.email "leapp+build+automation@not-for-real.leapp"

# Update data
mv -f ../discover.json files/discover.json

# Stage and commit
git add files/discover.json
git commit -s -m "Leapp dashboard discover for ${TRAVIS_COMMIT}" --allow-empty

# Push changes
git push origin master
