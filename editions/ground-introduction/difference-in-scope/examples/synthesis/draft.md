# Reference-channel calibration

## Background
Temperature drift can bias uncorrected sensor readings.[^drift]

## Related work
Drain and Li examined constant-temperature drift,[^static] whereas Mora evaluated paired reference channels at a field site.[^field]

## Research gap
The indoor tests leave outdoor operating conditions open.[^indoor] Rainfall also lay outside the field comparison.[^rain]

## Contributions
Our logger records reference pulses through wet and dry intervals at a 20 s sampling interval.[^own]

[^drift]: static.md | Temperature drift biases readings in uncorrected sensors.
[^static]: static.md | Drain and Li measured drift under constant temperature.
[^field]: field.md | Mora compared two reference channels at a field site.
[^indoor]: static.md | Their apparatus was tested only indoors.
[^rain]: field.md | Rainfall was not evaluated.
[^own]: our-log.txt | The logger records reference pulses during wet and dry intervals. The calibration circuit sampled every 20 s.
