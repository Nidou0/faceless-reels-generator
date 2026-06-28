# TikTok Developer App — Use Case Description

## App name
Faceless Reels Generator (personal use)

## What the app does
A personal content-scheduling tool that generates short-form narrated videos
(AI-written scripts, text-to-speech voiceover, background footage, burned-in
captions) and publishes them to the operator's own TikTok account on a
scheduled basis. This is a single-user personal automation tool, not a
multi-tenant SaaS product.

## Why we need the Content Posting API
To publish the generated videos directly to the operator's own TikTok
account without manual upload, the same way an existing scheduling tool
(e.g. Buffer, Later, Hootsuite) posts on a user's behalf.

## Scopes requested
- `video.publish` — required to post the generated videos directly to the
  authenticated account.

## How it will be tested in sandbox
1. Authenticate via OAuth as the developer's own TikTok account.
2. Call the Content Posting API `init` endpoint with a locally generated
   MP4 file.
3. Confirm the post appears on the authenticated account (private visibility
   while unaudited, as required).
4. Demo video will show this end-to-end flow: triggering a post from the
   app, and the resulting video appearing on the TikTok account.

## Who uses this app
Single user (the developer/operator only). No other TikTok accounts are
posted to or accessed.
