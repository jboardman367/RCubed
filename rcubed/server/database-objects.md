# There's probably a file format for this that I don't know

## Model

- (pkey) id: string
- runName: string
- botName: string
- created: integer
- mu: float
- sigma: float

## Files
- (pkey) id: string
- (fkey) modelId: string
- path: string

## (Not implemented) Web Links
- (pkey) id: string
- (fkey) modelId: string
- url: string
