"""Tests for MCP tool name conversion utilities."""

from omniforge.mcp.naming import make_omniforge_tool_name, to_snake_case


class TestToSnakeCase:
    def test_camel_case(self) -> None:
        assert to_snake_case("searchRepos") == "search_repos"

    def test_pascal_case(self) -> None:
        assert to_snake_case("ListDirectory") == "list_directory"

    def test_kebab_case(self) -> None:
        assert to_snake_case("list-directory") == "list_directory"

    def test_already_snake_case(self) -> None:
        assert to_snake_case("read_file") == "read_file"

    def test_space_separated(self) -> None:
        assert to_snake_case("read file") == "read_file"

    def test_acronym_sequence(self) -> None:
        assert to_snake_case("APIClient") == "api_client"

    def test_multiple_underscores_collapsed(self) -> None:
        assert to_snake_case("read__file") == "read_file"

    def test_all_uppercase(self) -> None:
        assert to_snake_case("API") == "api"

    def test_mixed_kebab_camel(self) -> None:
        assert to_snake_case("get-FileList") == "get_file_list"

    def test_single_word(self) -> None:
        assert to_snake_case("search") == "search"

    def test_numbers_preserved(self) -> None:
        assert to_snake_case("getV2Data") == "get_v2_data"


class TestMakeOmniforgeToolName:
    def test_basic(self) -> None:
        assert make_omniforge_tool_name("github", "searchRepos") == "mcp__github__search_repos"

    def test_kebab_server_name(self) -> None:
        assert (
            make_omniforge_tool_name("my-server", "ListDirectory")
            == "mcp__my_server__list_directory"
        )

    def test_already_snake_case(self) -> None:
        assert make_omniforge_tool_name("filesystem", "read_file") == "mcp__filesystem__read_file"

    def test_pascal_server_name(self) -> None:
        assert make_omniforge_tool_name("MyServer", "doThing") == "mcp__my_server__do_thing"

    def test_format_has_double_underscores(self) -> None:
        result = make_omniforge_tool_name("s", "t")
        assert result.startswith("mcp__")
        assert result.count("__") == 2

    def test_starts_with_lowercase(self) -> None:
        result = make_omniforge_tool_name("GitHub", "SearchRepos")
        assert result[0].islower()
