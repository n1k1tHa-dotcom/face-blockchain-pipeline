# Face ID → Web Search → Blockchain Verification

**HH Goa 2026 Shortlisting Task 3** — a pipeline that takes a face scan as input,
finds a matching post on the web / social media, and anchors the discovered data
on a blockchain to create a tamper-evident, re-verifiable record.

```
 Face scan input
      │
      ▼
 [1] Face detection & crop        (OpenCV Haar cascade)
      │
      ▼
 [2] Web / social-media search    (Google Lens reverse-image search via Serper API,
      │                            or interactive manual search fallback)
      ▼
 [3] Blockchain upload            (SHA-256 fingerprint of the discovered post data)
      │
      ▼
 [4] Re-verification              (fingerprint checked against the on-chain record)
```

---

## What it does

1. **Face identification** — detects a front-facing face in any input image and
   saves a padded crop (`face_crop.jpg`) using OpenCV's Haar cascade detector.
2. **Web / social-media search** — performs a **real, live search**: the face
   crop is uploaded to a temporary public image host and fed into **Google Lens
   reverse-image search** (via the [Serper](https://serper.dev/) API). The top
   matching result — post URL, image URL, title/caption, source page — becomes
   the discovered post. Nothing is hardcoded or pre-picked.
   - If no Serper API key is configured (or the API call fails), the pipeline
     falls back to an **interactive mode**: it prints instructions and accepts
     the URL of a genuine matching post you found yourself.
3. **Blockchain verification** — a SHA-256 fingerprint of the discovered post
   metadata (post URL, image URL, caption, profile URL) is stored on-chain.
   The pipeline then re-reads the record and proves the exact fingerprint
   exists, so any tampering with the post data would break verification.

---

## Which blockchain is used

| Mode | Network | When it is used |
| --- | --- | --- |
| **Sepolia testnet** (default goal) | Ethereum Sepolia (`chainId 11155111`) | `SEPOLIA_RPC_URL`, `PRIVATE_KEY` and `CONTRACT_ADDRESS` are all set in `.env` |
| **Local simulated chain** (fallback) | `.local_chain.json` — a hash-chained, persisted local ledger | any of the three Sepolia values is missing |

The smart contract (`contracts/FacePostAnchor.sol.txt`) keeps a
`mapping(bytes32 => bool)` of anchored content hashes with an `anchor(bytes32)`
write function and a `verify(bytes32) view` read function. Every anchor emits a
`HashAnchored` event with the hash, submitter and timestamp.

**Why both?** The real Sepolia testnet gives a genuine public, tamper-evident
record. The local simulated chain guarantees the demo runs end to end even when
you don't have test ETH or an RPC endpoint handy (the spec explicitly allows a
local/simulated chain, as long as re-verification can be demonstrated). The
pipeline picks the mode automatically and prints which one it used.

---

## How to run

### 1. Setup

```bash
python -m venv .venv
# Windows:
.venv\Scripts\pip install -r requirements.txt
# macOS / Linux:
.venv/bin/pip install -r requirements.txt

cp .env.example .env
```

Optional configuration in `.env`:

- `SERPER_API_KEY` — free key from https://serper.dev/ (enables fully automated
  search). Leave blank to use the interactive fallback.
- `SEPOLIA_RPC_URL`, `PRIVATE_KEY`, `CONTRACT_ADDRESS` — enable the real
  Sepolia testnet. Leave blank to use the local simulated chain.

### 2. Run the pipeline

```bash
# Windows:
.venv\Scripts\python main.py path\to\your_face_photo.jpg
# macOS / Linux:
.venv/bin/python main.py path/to/your_face_photo.jpg
```

The pipeline prints every step, shows the discovered post, the blockchain
anchor result, and the final verification verdict, then saves everything to
`result.json`.

> Tip: use a photo of someone with a public web presence (e.g. a well-known
> public figure's photo) so the reverse-image search finds a real matching post.

### 3. (Optional) Use the real Sepolia testnet

1. Create a test wallet and fund it with Sepolia test ETH from a free faucet
   (e.g. https://alchemy.com/faucets/ethereum-sepolia).
2. Fill `SEPOLIA_RPC_URL` and `PRIVATE_KEY` in `.env`.
3. Deploy the contract:

   ```bash
   .venv\Scripts\python deploy_contract.py
   ```

4. Copy the printed `CONTRACT_ADDRESS` into `.env`.
5. Run `main.py` again — it now anchors to and verifies against Sepolia.
   The anchor result includes the on-chain transaction hash and block number,
   which you can view on https://sepolia.etherscan.io/.

---

## Project structure

```
main.py                        # end-to-end pipeline orchestrator
face_module.py                 # face detection + cropping (OpenCV)
search_module.py               # reverse-image search (Serper Lens API + interactive fallback)
blockchain_module.py           # hashing, anchoring & verification (Sepolia + local chain)
deploy_contract.py             # deploys the Solidity contract to Sepolia
contracts/FacePostAnchor.sol.txt  # Solidity contract: anchor() / verify()
test_face.jpg                  # sample input image
result.json                    # full run output (generated)
.env.example                   # configuration template
```

---

## Known limitations

- **Reverse-image search quality** depends on the subject having matching images
  publicly indexed. A random/private face will legitimately return no strong
  match — use a photo of someone with a public web presence for the demo.
- The face crop is uploaded to a **public temporary image host** during the
  automated search step. The file persists on that host's servers.
- Google Lens matches visually similar images, not verified identity. The
  pipeline proves *this data was found and anchored*, not that the face
  belongs to the account that posted it.
- The local simulated chain is a single-node, file-backed ledger — suitable for
  a demo, not for production-grade security. Use the Sepolia mode for a real
  on-chain record.
- Serper's Lens endpoint is rate-limited by your free-tier quota (3 credits per
  Lens query).

---

## Submission checklist

- [x] Face scan input → real web/social search → blockchain upload/verification
- [x] Genuine search step (no hardcoded results)
- [x] On-chain record + re-verification demonstrated
- [x] No website needed — CLI pipeline only
- [ ] GitHub repo pushed with this README
- [ ] Screen recording of the working pipeline + link