# Contributing to HandheldHero

HandheldHero is supposed to make handheld setup less annoying. The code should follow the same rule.

If I open a file six months from now and need to stare at it for ten minutes before I can tell what it is doing, the code is not done yet.

## Keep it readable

A few rules I want to keep around this project:

- Use normal names. `firmware_path` is better than `fp2`.
- Keep functions focused enough that somebody can read them without building a conspiracy board.
- Comment the **reason** for weird behavior, not every obvious Python statement.
- If an upstream project does something strange, leave a comment explaining the strange thing.
- If a safety check exists because removing it could trash an SD card, say that clearly.
- Prefer boring code that is easy to debug over clever code that saves four lines.
- Error messages should tell a normal person what went wrong and what they can do about it.

## Comment style

Comments should sound like a person explaining the code to another person.

Good:

```python
# Hekate and Atmosphere are root-level packages, so merge them onto the SD.
# Do not wipe the card first. People tend to keep useful stuff on these things.
```

Also good:

```python
# DuckStation uses a rolling release instead of a normal version number.
# Show the release date rather than pretending "latest" is a useful version.
```

Not useful:

```python
# Increment count by one
count += 1
```

And definitely not this:

```python
# This function facilitates the orchestration of dynamic software-component acquisition.
```

Nobody talks like that.

## External downloads

If HandheldHero downloads something automatically, it should come from a source we can identify and explain.

For normal Android apps, Obtainium should handle updates whenever it already does the job well.

For Switch base components, prefer official upstream projects and record the version that was installed.

Do not add mystery mirrors because they make one install path slightly easier.

## Files supplied by the user

HandheldHero can work with user-provided BIOS files, firmware, and local packages.

The tool should not quietly download copyrighted/questionable files just because a filename is missing.

Local selections should be obvious in the UI and validated before anything gets copied.

## SD-card changes

Anything that can overwrite existing files deserves extra care.

- Back up overwritten files when practical.
- Merge known package layouts instead of deleting whole folders.
- Reject suspicious archive paths like `../whatever`.
- Keep Dry Run honest when adding a new operation.
- Verify the result after writing it.

Basically: **do not make the one-click button exciting.**

## Version handling

Show the version users are actually getting whenever upstream exposes one.

If the project uses a rolling release, date, build number, or other weird scheme, show that honestly.

Do not turn `latest` into `v1.0` because it looks nicer.

## Before committing

At minimum:

1. Make sure the Python source compiles.
2. Test download/source resolution for anything you changed.
3. Use a temporary/fake SD root for Switch filesystem changes before trying a real card.
4. Make sure Dry Run agrees with what Run Setup actually does.
5. Make sure build folders, downloaded APKs, caches, backups, or personal paths did not sneak into the commit.

If the change touches real hardware, test like you would prefer not to spend the rest of the evening fixing it.
