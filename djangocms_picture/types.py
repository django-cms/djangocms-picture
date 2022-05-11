from collections import namedtuple

AlternativePictureData = namedtuple(
    "AlternativePictureData", ["size_id", "picture", "viewport_width", "sizes_data"]
)
SourceData = namedtuple(
    "SourceData", ["mime_type", "picture", "srcset", "sizes", "media"]
)
SizesAttributeData = namedtuple(
    "SizeVersionsData", ["breakpoint", "viewport_width", "srcset_sizes"]
)
