# Git & GitHub Setup Instructions

Follow these steps after opening the folder in VS Code.

---

## Step 1 — Open the folder in VS Code

File → Open Folder → select the `ecommerce-data-cleaning` folder.

---

## Step 2 — Open the VS Code terminal

Press  Ctrl + ` (backtick)  to open the integrated terminal.

---

## Step 3 — Initialise a local Git repo

```bash
git init
git add .
git commit -m "Initial commit: raw data, cleaning script, clean output, README"
```

---

## Step 4 — Create a repo on GitHub

1. Go to https://github.com/new
2. Repository name: `ecommerce-data-cleaning`
3. Description (optional): `End-to-end data cleaning project on an East Africa e-commerce orders dataset`
4. Set to **Public** (so it appears on your portfolio)
5. **Do NOT** tick "Add a README file" or "Add .gitignore" — you already have them
6. Click **Create repository**

---

## Step 5 — Link your local repo to GitHub and push

GitHub will show you these commands after you create the repo. Run them in the VS Code terminal:

```bash
git remote add origin https://github.com/YOUR_USERNAME/ecommerce-data-cleaning.git
git branch -M main
git push -u origin main
```

Replace `YOUR_USERNAME` with your actual GitHub username.

---

## Step 6 — Verify

Go to `https://github.com/YOUR_USERNAME/ecommerce-data-cleaning` in your browser.
You should see all 5 files and your README rendered on the page.

---

## Future updates

After making any changes to the script or README:

```bash
git add .
git commit -m "Your message describing what changed"
git push
```

---

## Optional: add a GitHub topic tag

On your GitHub repo page, click the gear icon next to **About** and add topics:
`data-cleaning`, `python`, `pandas`, `portfolio`, `east-africa`

This makes your repo discoverable in GitHub search.
