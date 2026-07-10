import pytest
from src.utils.sanitize import (
    sanitize_contact_name,
    is_valid_contact_name,
    is_valid_uuid,
    generate_client_id,
)


class TestSanitizeContactName:
    def test_keeps_valid_chars(self):
        assert sanitize_contact_name("alice") == "alice"
        assert sanitize_contact_name("Bob_02") == "Bob_02"
        assert sanitize_contact_name("hello-world") == "hello-world"
        assert sanitize_contact_name("test.file") == "test.file"
        assert sanitize_contact_name("contact name") == "contact name"

    def test_replaces_caret(self):
        assert sanitize_contact_name("Unravelling^Thoughts") == "Unravelling_Thoughts"

    def test_replaces_special_chars(self):
        assert sanitize_contact_name("hello!world") == "hello_world"
        assert sanitize_contact_name("test@name") == "test_name"
        assert sanitize_contact_name("dollar$ign") == "dollar_ign"
        assert sanitize_contact_name("percent%") == "percent_"
        assert sanitize_contact_name("amp&ersand") == "amp_ersand"
        assert sanitize_contact_name("parens(test)") == "parens_test_"
        assert sanitize_contact_name("plus+plus") == "plus_plus"
        assert sanitize_contact_name("equal=sign") == "equal_sign"
        assert sanitize_contact_name("bracket[test]") == "bracket_test_"
        assert sanitize_contact_name("brace{test}") == "brace_test_"
        assert sanitize_contact_name("tilde~") == "tilde_"
        assert sanitize_contact_name("backtick`") == "backtick_"
        assert sanitize_contact_name("quote'test") == "quote_test"
        assert sanitize_contact_name('quote"test') == "quote_test"
        assert sanitize_contact_name("angle<test>") == "angle_test_"
        assert sanitize_contact_name("pipe|test") == "pipe_test"
        assert sanitize_contact_name("question?mark") == "question_mark"
        assert sanitize_contact_name("slash/test") == "slash_test"
        assert sanitize_contact_name("back\\slash") == "back_slash"
        assert sanitize_contact_name("colon:test") == "colon_test"
        assert sanitize_contact_name("asterisk*") == "asterisk_"

    def test_strips_leading_trailing_dot_space(self):
        assert sanitize_contact_name(".hello") == "hello"
        assert sanitize_contact_name("hello.") == "hello"
        assert sanitize_contact_name(" hello ") == "hello"

    def test_inner_dots_kept(self):
        assert sanitize_contact_name("hello.world") == "hello.world"
        assert sanitize_contact_name("john.doe") == "john.doe"

    def test_truncates_to_100_chars(self):
        long_name = "a" * 150
        result = sanitize_contact_name(long_name)
        assert len(result) == 100
        assert result == "a" * 100

    def test_empty_returns_unknown(self):
        assert sanitize_contact_name("") == "unknown"
        assert sanitize_contact_name("   ") == "unknown"
        assert sanitize_contact_name("...") == "unknown"


class TestIsValidContactName:
    def test_valid_names(self):
        assert is_valid_contact_name("alice")
        assert is_valid_contact_name("Bob_02")
        assert is_valid_contact_name("hello-world")
        assert is_valid_contact_name("test.file")
        assert is_valid_contact_name("contact name")
        assert is_valid_contact_name("a" * 100)

    def test_invalid_names(self):
        assert not is_valid_contact_name("")
        assert not is_valid_contact_name("a" * 101)
        assert not is_valid_contact_name("hello^world")
        assert not is_valid_contact_name("test!name")
        assert not is_valid_contact_name("at@sign")
        assert not is_valid_contact_name("dollar$")
        assert not is_valid_contact_name("percent%")
        assert not is_valid_contact_name("question?")
        assert not is_valid_contact_name("slash/test")
        assert not is_valid_contact_name("back\\slash")
        assert not is_valid_contact_name("colon:test")
        assert not is_valid_contact_name("asterisk*")
        assert not is_valid_contact_name("quote'test")
        assert not is_valid_contact_name('quote"test')


class TestIsValidUuid:
    def test_valid_uuids(self):
        assert is_valid_uuid("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
        assert is_valid_uuid("00000000-0000-0000-0000-000000000000")
        assert is_valid_uuid("ABCDEFAB-1234-5678-9ABC-DEF012345678")

    def test_invalid_uuids(self):
        assert not is_valid_uuid("")
        assert not is_valid_uuid("not-a-uuid")
        assert not is_valid_uuid("a1b2c3d4e5f67890abcdef1234567890")
        assert not is_valid_uuid("1234")
        assert not is_valid_uuid(None)


class TestGenerateClientId:
    def test_returns_uuid_string(self):
        cid = generate_client_id()
        assert isinstance(cid, str)
        assert is_valid_uuid(cid)

    def test_unique(self):
        ids = {generate_client_id() for _ in range(100)}
        assert len(ids) == 100
