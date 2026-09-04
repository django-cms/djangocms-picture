from collections.abc import Mapping

from django.test import SimpleTestCase

from djangocms_picture.backends import (
    BackendCapabilities,
    BaseImageAsset,
    ImageInfo,
    PictureReference,
    Rendition,
    RenditionSpec,
)
from djangocms_picture.rendering import build_srcset, calculate_size


class StubImageAsset(BaseImageAsset):
    capabilities = BackendCapabilities(responsive=True)

    def __init__(
        self,
        *,
        width: int | None,
        rendered_widths: Mapping[int, int | None] | None = None,
    ) -> None:
        self.reference = PictureReference(backend="stub", id="image")
        self.info = ImageInfo(label="Stub", width=width, height=600)
        self.rendered_widths = rendered_widths or {}
        self.requested_specs: list[RenditionSpec] = []

    def get_original(self) -> Rendition:
        return Rendition(url="/original.jpg", width=self.info.width, height=self.info.height)

    def get_rendition(self, spec: RenditionSpec) -> Rendition:
        self.requested_specs.append(spec)
        rendered_width = self.rendered_widths.get(spec.width or 0, spec.width)
        return Rendition(
            url=f"/{spec.width}.jpg",
            width=rendered_width,
            height=spec.height,
        )


class CalculateSizeTestCase(SimpleTestCase):
    def test_uses_intrinsic_dimensions_without_requested_size(self) -> None:
        spec = calculate_size(ImageInfo(label="Image", width=800, height=600))

        self.assertEqual(spec, RenditionSpec(width=800, height=600))

    def test_preserves_explicit_dimensions_and_flags(self) -> None:
        spec = calculate_size(
            ImageInfo(label="Image", width=800, height=600),
            width=321.9,
            height=123.8,
            crop=True,
            upscale=True,
        )

        self.assertEqual(
            spec,
            RenditionSpec(width=321, height=123, crop=True, upscale=True),
        )

    def test_derives_crop_height_for_landscape_and_portrait_images(self) -> None:
        landscape = calculate_size(
            ImageInfo(label="Landscape", width=800, height=600),
            width=1000,
            crop=True,
        )
        portrait = calculate_size(
            ImageInfo(label="Portrait", width=600, height=800),
            width=1000,
            crop=True,
        )

        self.assertEqual((landscape.width, landscape.height), (1000, 618))
        self.assertEqual((portrait.width, portrait.height), (1000, 1618))

    def test_derives_crop_width_for_landscape_and_portrait_images(self) -> None:
        landscape = calculate_size(
            ImageInfo(label="Landscape", width=800, height=600),
            height=1000,
            crop=True,
        )
        portrait = calculate_size(
            ImageInfo(label="Portrait", width=600, height=800),
            height=1000,
            crop=True,
        )

        self.assertEqual((landscape.width, landscape.height), (1618, 1000))
        self.assertEqual((portrait.width, portrait.height), (618, 1000))

    def test_supports_missing_image_metadata(self) -> None:
        spec = calculate_size(None, width=320, crop=True)

        self.assertEqual(spec, RenditionSpec(width=320, crop=True))


class BuildSrcsetTestCase(SimpleTestCase):
    def test_returns_no_sources_for_missing_or_nonresponsive_assets(self) -> None:
        asset = StubImageAsset(width=800)
        asset.capabilities = BackendCapabilities(responsive=False)

        self.assertEqual(build_srcset(None, widths=[320]), [])
        self.assertEqual(build_srcset(asset, widths=[320]), [])

    def test_returns_no_sources_without_a_source_width(self) -> None:
        asset = StubImageAsset(width=None)

        self.assertEqual(build_srcset(asset, widths=[320]), [])

    def test_filters_sorts_and_deduplicates_rendered_widths(self) -> None:
        asset = StubImageAsset(
            width=1000,
            rendered_widths={320: 300, 640: 300, 800: None},
        )

        sources = build_srcset(
            asset,
            widths=[1000, "800", 640, 320, 320],
            crop=True,
            upscale=True,
        )

        self.assertEqual(
            sources,
            [
                (300, Rendition(url="/320.jpg", width=300, height=320)),
                (800, Rendition(url="/800.jpg", width=None, height=800)),
            ],
        )
        self.assertEqual(
            asset.requested_specs,
            [
                RenditionSpec(width=320, height=320, crop=True, upscale=True),
                RenditionSpec(width=640, height=640, crop=True, upscale=True),
                RenditionSpec(width=800, height=800, crop=True, upscale=True),
            ],
        )

    def test_explicit_source_width_overrides_image_metadata(self) -> None:
        asset = StubImageAsset(width=1200)

        sources = build_srcset(asset, widths=[320, 640], width=500)

        self.assertEqual([width for width, _ in sources], [320])
