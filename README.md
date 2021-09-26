# Google Photos Filter
This allows you to filter your Google Photos for various criteria

## How to use
```
docker run --rm -it -v /path/to/google-photos-filter/secrets:/app/secrets -v /path/to/google-photos-filter/results:/app/results --name google-photos-filter paranerd/google-photos-filter --filter <filter-name>
```

## Supported filters
### No album
Filter name: `no-album`

What it does: Filters for all photos that are not part of an album
