from pppoe_cred_helper.parse.extract import parse_pap_line, mask_password, Credentials

def test_parse_pap_line_valid():
    line = "  1 0.000000000       10.0.0.1 → 10.0.0.2         PAP 60 Authenticate-Request (Peer-ID='user@isp', Password='secret_password')"
    expected = Credentials(username="user@isp", password="secret_password")
    assert parse_pap_line(line) == expected

def test_parse_pap_line_invalid():
    line = "  1 0.000000000       10.0.0.1 → 10.0.0.2         TCP 60 443 → 54321 [ACK] Seq=1 Ack=1 Win=64240 Len=0"
    assert parse_pap_line(line) is None

def test_mask_password():
    assert mask_password("password") == "p******d"
    assert mask_password("abc") == "a*c"
    assert mask_password("12") == "**"
    assert mask_password("a") == "*"
