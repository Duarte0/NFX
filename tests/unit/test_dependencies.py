from nfx.infrastructure.dependencies import ServiceDependencies


def test_dependency_check_is_injectable_and_reports_only_service_names() -> None:
    dependencies = ServiceDependencies(
        database_url="postgresql://not-disclosed",
        minio_endpoint="http://not-disclosed",
        minio_access_key="not-disclosed",
        minio_secret_key="not-disclosed",
        minio_bucket="test-bucket",
        postgres_probe=lambda _: None,
        object_probe=lambda *_: (_ for _ in ()).throw(RuntimeError("not-disclosed")),
        schema_probe=lambda: None,
    )

    result = dependencies.check()

    assert not result.ready
    assert result.unavailable == ("minio",)


def test_schema_incompatibility_makes_readiness_fail_without_details() -> None:
    dependencies = ServiceDependencies(
        database_url="postgresql://not-disclosed",
        minio_endpoint="http://not-disclosed",
        minio_access_key="not-disclosed",
        minio_secret_key="not-disclosed",
        minio_bucket="test-bucket",
        postgres_probe=lambda _: None,
        object_probe=lambda *_: None,
        schema_probe=lambda: (_ for _ in ()).throw(RuntimeError("not-disclosed")),
    )

    assert dependencies.check().unavailable == ("schema",)
