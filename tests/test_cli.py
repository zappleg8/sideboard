from sideboard.cli import parse_args


def test_parse_args_default():
    args = parse_args([])
    assert args.command == "play"
    assert args.difficulty == "club"
    assert args.color is None


def test_parse_args_difficulty():
    args = parse_args(["--difficulty", "casual"])
    assert args.difficulty == "casual"


def test_parse_args_white():
    args = parse_args(["--white"])
    assert args.color == "white"


def test_parse_args_black():
    args = parse_args(["--black"])
    assert args.color == "black"


def test_parse_args_resume():
    args = parse_args(["resume"])
    assert args.command == "resume"


def test_parse_args_stats():
    args = parse_args(["stats"])
    assert args.command == "stats"


def test_parse_args_export():
    args = parse_args(["export"])
    assert args.command == "export"


def test_parse_args_install_skill():
    args = parse_args(["install-skill"])
    assert args.command == "install-skill"


def test_parse_args_bridge():
    args = parse_args(["bridge", "new"])
    assert args.command == "bridge"
