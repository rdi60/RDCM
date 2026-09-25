# Updating this website

All the text on the site lives in one file: **`data/content.js`**.
Open it in any text editor, change the text between the quotes, save, and
refresh the page in your browser — no other files need to change.

## Updating text

Each section of the site maps to a section of that file:

- `doctor` — name, credentials, title
- `hero` — the headline and short bio at the top of the page
- `hospital` — Rajan Dental Hospital's description and photo
- `publications.international` / `publications.national` — one entry per paper
- `conferences.internationalInvited` / `nationalInvited` / `workshopsOrganized` — one entry per talk or workshop
- `awards` — recognitions, leadership positions, examinerships, teaching
- `contact` — email, address, phone

To add a new publication or conference entry, copy an existing `{ ... }` line
in that list and edit its values — just keep the commas between entries.

## Updating photos

1. Save the new photo into the `images/` folder (e.g. `images/doctor-portrait.jpg`).
2. In `data/content.js`, find `photos.doctorPortrait` and change it from `null`
   to the path in quotes, e.g. `doctorPortrait: "images/doctor-portrait.jpg"`.
3. Refresh the page — the placeholder is replaced automatically.

The hospital photo works the same way: it's `hospital.photo` in the same file.

## Filling in contact details

`contact.address` and `contact.phone` are currently empty (`""`) because
they weren't published anywhere on the old site. Add them in quotes, e.g.:

```js
contact: {
  email: "drgunaseelan@rajandental.com",
  address: "Rajan Dental Hospital, Mylapore, Chennai",
  phone: "+91 44 XXXX XXXX",
},
```

Once either is filled in, it appears automatically under the Contact section.

## Previewing changes locally

This is a plain HTML/CSS/JS site with no build step. To preview it on your
own computer, open a terminal in this folder and run:

```
python3 -m http.server 8000
```

Then open `http://localhost:8000` in a browser.
