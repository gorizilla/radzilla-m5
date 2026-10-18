# Contributing

Thanks for your interest in RadZilla M5! It is an experimental hobby
project – ideas, bug reports and improvements are welcome.

## Bug reports and ideas

Please open an issue and include:

- RadZilla M5 version (shown on the splash screen and in `config.py`),
- hardware (Core2 version, RadiaCode model and firmware),
- what you did, what you expected and what happened,
- the Thonny shell output if there is an error.

Never post WiFi passwords or other personal data (`wifi.json` is not part
of the repository for that reason).

## Pull requests

- Keep changes small and focused, one topic per pull request.
- Keep the existing structure: hardware-specific code in `devices/`, logic
  without hardware in `core/`, drawing in `ui/`, settings in `config.py`.
- Code, comments and documentation in English.
- Nothing may be written to the RadiaCode except the functions documented
  in [NOTICE.md](NOTICE.md). Never send `PLAY_SIGNAL` value 2 (permanent
  alarm that can only be stopped by switching the RadiaCode off).
- Describe how you tested the change (device, firmware).

## Rights to contributions

By submitting a contribution (code, documentation, images, sounds or other
material) you confirm that it is your own work and that you have the right
to submit it, and you agree that:

1. your contribution is published under the license of this project
   ([CC BY-NC-SA 4.0](LICENSE.md)), and
2. you grant the author of RadZilla M5 (Shimizilla) a **non-exclusive,
   worldwide, royalty-free, perpetual and irrevocable right** to use,
   modify, sublicense and distribute your contribution **also commercially**
   and under other license terms (e.g. for commercial licenses of
   RadZilla M5).

You keep the copyright of your contribution and may use it yourself in any
way you like. Contributors are credited in the changelog.
