from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_verify_fullstack_contains_t1_6a_attachment_smoke_contract():
    script = (ROOT / "scripts" / "verify-fullstack.ps1").read_text(encoding="utf-8")

    assert "== T1.6A attachment smoke ==" in script
    assert "Invoke-AttachmentUpload" in script
    assert "manager uploads sample attachment" in script
    assert "director upload rejected" in script
    assert "cross-project attachment access rejected" in script
    assert "download after delete rejected" in script
    assert "/attachments?entity_type=sample" in script
    assert "/attachments/" in script


def test_t1_6a_attachment_documentation_covers_required_sections():
    doc = (ROOT / "docs" / "T1.6A_ATTACHMENTS.md").read_text(encoding="utf-8")

    for heading in [
        "附件实体契约",
        "entity_type 与内部模型映射",
        "API 列表",
        "权限矩阵",
        "文件大小/类型限制",
        "本地存储配置",
        "对象存储预留点",
        "已知限制和技术债",
    ]:
        assert heading in doc
    assert "Daily report attachments require exactly one linked project." in doc
