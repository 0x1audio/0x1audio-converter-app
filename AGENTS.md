# Building this app

This folder is the whole app.

- `app.py` is the work. `@ox.screen` turns `convert` into the Audio Converter screen.
- `app.json` names the app.
- `ox eject` writes `ui/App.tsx` when the screen needs a custom layout.

`convert` takes files the user picks and a format. It yields `ox.sound`, which adds the converted file to the Library.
`ox.test(convert, files=[...], format="wav")` runs it without the desktop.
Permissions come from `ox.Files` and `ox.sound`.
