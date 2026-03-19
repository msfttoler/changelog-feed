"""Unit tests for parity matrix."""

from src.parity import IDES, get_parity_matrix


class TestParityMatrix:
    def test_returns_ides_list(self):
        m = get_parity_matrix()
        assert "ides" in m
        assert isinstance(m["ides"], list)
        assert len(m["ides"]) == 7

    def test_expected_ides(self):
        m = get_parity_matrix()
        assert "VS Code" in m["ides"]
        assert "Visual Studio" in m["ides"]
        assert "JetBrains" in m["ides"]
        assert "Neovim" in m["ides"]
        assert "Eclipse" in m["ides"]
        assert "Xcode" in m["ides"]

    def test_has_categories(self):
        m = get_parity_matrix()
        assert "categories" in m
        assert len(m["categories"]) == 5

    def test_category_structure(self):
        m = get_parity_matrix()
        for cat in m["categories"]:
            assert "category" in cat
            assert "features" in cat
            assert isinstance(cat["category"], str)
            assert isinstance(cat["features"], list)
            assert len(cat["features"]) > 0

    def test_feature_structure(self):
        m = get_parity_matrix()
        for cat in m["categories"]:
            for feat in cat["features"]:
                assert "name" in feat
                assert "support" in feat
                assert isinstance(feat["name"], str)
                assert isinstance(feat["support"], dict)

    def test_support_values_valid(self):
        m = get_parity_matrix()
        valid = {True, False, "partial"}
        for cat in m["categories"]:
            for feat in cat["features"]:
                for ide, status in feat["support"].items():
                    assert status in valid, f"{feat['name']}[{ide}] = {status!r}"

    def test_feature_support_covers_all_ides(self):
        m = get_parity_matrix()
        for cat in m["categories"]:
            for feat in cat["features"]:
                for ide in IDES:
                    assert ide in feat["support"], (
                        f"Missing {ide} in {feat['name']}"
                    )

    def test_code_completions_universal(self):
        m = get_parity_matrix()
        code_gen = m["categories"][0]
        completions = code_gen["features"][0]
        assert completions["name"] == "Code Completions"
        for ide in IDES:
            assert completions["support"][ide] is True

    def test_category_names(self):
        m = get_parity_matrix()
        names = [c["category"] for c in m["categories"]]
        assert "Code Generation & Editing" in names
        assert "Chat & Agent" in names
        assert "Context & Intelligence" in names
        assert "Extensibility & Customization" in names
        assert "DevOps & CLI" in names
