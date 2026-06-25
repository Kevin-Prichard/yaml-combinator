# yaml-combinator

*`yc` does two things well:* 
1. Merge yaml files together with an import directive:

`#!import <path>`

2. interpolates \*VAR references.


The intent is directed document composition and variable sharing across documents.


## What's the point?
Best for use-cases where your existing YAML-consuming ecosystem doesn't provide templating, merging or interpolation.

You've got multiple YAML files — configs, templates, variables.  You want to produce a finished singular document: 

- **Combines** multiple YAML files into a single, clean output
- **Resolves `#!import` directives** — one file can pull in another, in a tree-shaped import hierarchy
- **Interpolates anchor variables** — define a value once with `&VAR_NAME`,
  and every `*VAR_NAME` reference across all your files gets the same value.


## Installation

```bash
uv pip install yaml-combinator
uv sync
```

## Usage
```
# Combine two files and print to stdout
uv run yc base.yaml overrides.yaml

# Write the result to a file instead
uv run yc base.yaml overrides.yaml -o combined.yaml

# Pull in as many files as you need — yc don't care
uv run yc defaults.yaml env.yaml secrets.yaml -o /dev/stdout
```

### The #!import Directive

Drop this line anywhere inside a YAML file and yc will inline the target file's contents right there, no questions asked:
```
# base.yaml
server:
  host: localhost

#!import "extras/logging.yaml"
```

Imports are resolved relative to the current working directory, and absolute paths are fine.

## Anchor Variable Interpolation

Define a variable on one line, reference it anywhere across the combined output:

```
# vars.yaml
platform: &PLATFORM bun
version:  &VERSION  "3.1.0"

# app.yaml
runtime: *PLATFORM      # becomes: runtime: bun
release: *VERSION       # becomes: release: "3.1.0"
```

The definition line stays intact. Only the *VAR_NAME aliases get swapped out. Last definition wins — just like in this town.

## Why this exists
Writing code-generation prompts in markdown, we were disappointed by limits in the resulting structure, and lack of reusability.

YAML provides structural improvements, but no interpolation, and no importing, linking or merging.

Sure, your coding agent can look across files and might piece together and understand that your separate documents are meant to be a cohesive unit, but we found the results pretty choppy and wildly different across agents and LLMs, from 2025 thru mid-2026.

## TO-DO
Provide a form of transclusion by allowing selective inclusion references by key path.  All values and subtrees in YAML are path-addressible, so this should be a minor deed.

Basic rule: You Get What You Ask For (YGWYAF)
- paths ending at a subtree will transclude the subtree and substitute it at the level of the path reference
- paths ending in a scalar type will replace the reference at that leaf point 

## Requirements

```
Python ≥ 3.10
PyYAML ≥ 6.0
```

## License

See [LICENSE](LICENSE).
