"""Tree-sitter based multi-language AST parser."""
from pathlib import Path
from typing import Optional
import tree_sitter

# Language registry - lazy loaded
_LANGUAGES: dict[str, tree_sitter.Language] = {}
_PARSERS: dict[str, tree_sitter.Parser] = {}

# File extension to language mapping
EXT_TO_LANG = {
    ".py": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "golang",
    ".rs": "rust",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "css",
    ".tf": "hcl",
    ".hcl": "hcl",
    ".toml": "toml",
}

# Symbol node types per language
SYMBOL_TYPES = {
    "python": {
        "class_definition": "class",
        "function_definition": "function",
        "decorated_definition": "decorated",
    },
    "javascript": {
        "class_declaration": "class",
        "function_declaration": "function",
        "method_definition": "method",
        "arrow_function": "function",
        "variable_declarator": "variable",
    },
    "typescript": {
        "class_declaration": "class",
        "function_declaration": "function",
        "method_definition": "method",
        "arrow_function": "function",
        "interface_declaration": "interface",
        "type_alias_declaration": "type",
    },
    "golang": {
        "function_declaration": "function",
        "method_declaration": "method",
        "type_declaration": "type",
        "type_spec": "type",
    },
    "rust": {
        "function_item": "function",
        "impl_item": "impl",
        "struct_item": "struct",
        "enum_item": "enum",
        "trait_item": "trait",
        "mod_item": "module",
    },
    "bash": {
        "function_definition": "function",
    },
    "json": {
        "pair": "key",
    },
    "yaml": {
        "block_mapping_pair": "key",
    },
    "html": {
        "element": "element",
        "script_element": "script",
        "style_element": "style",
    },
    "css": {
        "rule_set": "rule",
        "media_statement": "media",
        "keyframes_statement": "keyframes",
    },
    "hcl": {
        "block": "block",
        "attribute": "attribute",
    },
    "toml": {
        "table": "table",
        "pair": "key",
    },
}


def _get_language(lang: str) -> Optional[tree_sitter.Language]:
    """Get tree-sitter Language object, lazy loading."""
    if lang in _LANGUAGES:
        return _LANGUAGES[lang]

    try:
        if lang == "python":
            import tree_sitter_python
            _LANGUAGES[lang] = tree_sitter.Language(tree_sitter_python.language())
        elif lang == "javascript":
            import tree_sitter_javascript
            _LANGUAGES[lang] = tree_sitter.Language(tree_sitter_javascript.language())
        elif lang == "typescript":
            import tree_sitter_typescript
            _LANGUAGES[lang] = tree_sitter.Language(tree_sitter_typescript.language_typescript())
        elif lang == "golang":
            import tree_sitter_go
            _LANGUAGES[lang] = tree_sitter.Language(tree_sitter_go.language())
        elif lang == "rust":
            import tree_sitter_rust
            _LANGUAGES[lang] = tree_sitter.Language(tree_sitter_rust.language())
        elif lang == "bash":
            import tree_sitter_bash
            _LANGUAGES[lang] = tree_sitter.Language(tree_sitter_bash.language())
        elif lang == "json":
            import tree_sitter_json
            _LANGUAGES[lang] = tree_sitter.Language(tree_sitter_json.language())
        elif lang == "yaml":
            import tree_sitter_yaml
            _LANGUAGES[lang] = tree_sitter.Language(tree_sitter_yaml.language())
        elif lang == "html":
            import tree_sitter_html
            _LANGUAGES[lang] = tree_sitter.Language(tree_sitter_html.language())
        elif lang == "css":
            import tree_sitter_css
            _LANGUAGES[lang] = tree_sitter.Language(tree_sitter_css.language())
        elif lang == "hcl":
            import tree_sitter_hcl
            _LANGUAGES[lang] = tree_sitter.Language(tree_sitter_hcl.language())
        elif lang == "toml":
            import tree_sitter_toml
            _LANGUAGES[lang] = tree_sitter.Language(tree_sitter_toml.language())
        else:
            return None
        return _LANGUAGES[lang]
    except ImportError:
        return None


def get_parser(lang: str) -> Optional[tree_sitter.Parser]:
    """Get tree-sitter Parser for a language."""
    if lang in _PARSERS:
        return _PARSERS[lang]

    language = _get_language(lang)
    if not language:
        return None

    parser = tree_sitter.Parser(language)
    _PARSERS[lang] = parser
    return parser


def detect_language(file_path: str) -> Optional[str]:
    """Detect language from file extension."""
    ext = Path(file_path).suffix.lower()
    return EXT_TO_LANG.get(ext)


def parse_file(file_path: str) -> Optional[tree_sitter.Tree]:
    """Parse a file and return the AST tree."""
    path = Path(file_path)
    if not path.exists():
        return None

    lang = detect_language(file_path)
    if not lang:
        return None

    parser = get_parser(lang)
    if not parser:
        return None

    try:
        source = path.read_bytes()
        return parser.parse(source)
    except Exception:
        return None


def get_node_text(node: tree_sitter.Node, source: bytes) -> str:
    """Extract text content of a node."""
    return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def get_symbol_name(node: tree_sitter.Node, source: bytes, lang: str) -> Optional[str]:
    """Extract symbol name from a node based on language."""
    if lang == "python":
        # For Python, name is in 'name' or 'identifier' child
        for child in node.children:
            if child.type == "identifier":
                return get_node_text(child, source)
            if child.type == "name":
                return get_node_text(child, source)
        # For decorated_definition, get the inner definition
        if node.type == "decorated_definition":
            for child in node.children:
                if child.type in ("function_definition", "class_definition"):
                    return get_symbol_name(child, source, lang)

    elif lang in ("javascript", "typescript"):
        for child in node.children:
            if child.type in ("identifier", "property_identifier"):
                return get_node_text(child, source)

    elif lang == "golang":
        for child in node.children:
            if child.type == "identifier":
                return get_node_text(child, source)
            if child.type == "type_spec":
                # For type declarations, get the name from type_spec
                for subchild in child.children:
                    if subchild.type == "type_identifier":
                        return get_node_text(subchild, source)

    elif lang == "rust":
        for child in node.children:
            if child.type in ("identifier", "type_identifier"):
                return get_node_text(child, source)

    elif lang == "bash":
        for child in node.children:
            if child.type == "word":
                return get_node_text(child, source)

    elif lang in ("json", "yaml", "toml"):
        for child in node.children:
            if child.type in ("string", "key", "bare_key"):
                text = get_node_text(child, source)
                return text.strip('"\'')

    elif lang == "hcl":
        # HCL blocks have: block_type, labels, body
        for child in node.children:
            if child.type == "identifier":
                return get_node_text(child, source)
            if child.type == "string_lit":
                text = get_node_text(child, source)
                return text.strip('"')

    return None


def extract_symbols_from_tree(
    tree: tree_sitter.Tree,
    source: bytes,
    lang: str,
    depth: int = 2,
    include_body: bool = False
) -> list[dict]:
    """Extract symbols from a parsed tree."""
    symbols = []
    symbol_types = SYMBOL_TYPES.get(lang, {})

    def process_node(node: tree_sitter.Node, parent_name: str = "", current_depth: int = 0):
        if current_depth > depth:
            return

        node_type = node.type
        if node_type in symbol_types:
            kind = symbol_types[node_type]
            name = get_symbol_name(node, source, lang)

            if name:
                name_path = f"{parent_name}/{name}" if parent_name else name
                symbol = {
                    "name": name,
                    "kind": kind,
                    "lineno": node.start_point[0] + 1,
                    "end_lineno": node.end_point[0] + 1,
                    "column": node.start_point[1],
                    "name_path": name_path,
                    "language": lang,
                }

                if include_body:
                    symbol["body"] = get_node_text(node, source)

                # Process children for nested symbols
                children = []
                for child in node.children:
                    child_symbols = []
                    process_child(child, name, current_depth + 1, child_symbols)
                    children.extend(child_symbols)

                if children:
                    symbol["children"] = children

                symbols.append(symbol)
                return  # Don't recurse further for this branch

        # Continue recursing for non-symbol nodes
        for child in node.children:
            process_node(child, parent_name, current_depth)

    def process_child(node: tree_sitter.Node, parent_name: str, current_depth: int, result: list):
        if current_depth > depth:
            return

        node_type = node.type
        if node_type in symbol_types:
            kind = symbol_types[node_type]
            name = get_symbol_name(node, source, lang)

            if name:
                name_path = f"{parent_name}/{name}"
                symbol = {
                    "name": name,
                    "kind": kind,
                    "lineno": node.start_point[0] + 1,
                    "end_lineno": node.end_point[0] + 1,
                    "column": node.start_point[1],
                    "name_path": name_path,
                    "language": lang,
                }
                if include_body:
                    symbol["body"] = get_node_text(node, source)
                result.append(symbol)

        for child in node.children:
            process_child(child, parent_name, current_depth + 1, result)

    process_node(tree.root_node)
    return symbols


def find_references_in_tree(
    tree: tree_sitter.Tree,
    source: bytes,
    symbol: str,
    lang: str
) -> list[dict]:
    """Find all references to a symbol in a parsed tree."""
    references = []
    source_lines = source.decode("utf-8", errors="replace").splitlines()

    def find_in_node(node: tree_sitter.Node):
        # Check if this node is an identifier matching our symbol
        if node.type in ("identifier", "property_identifier", "type_identifier", "word"):
            text = get_node_text(node, source)
            if text == symbol:
                line = node.start_point[0]
                references.append({
                    "line": line + 1,
                    "column": node.start_point[1] + 1,
                    "text": source_lines[line] if line < len(source_lines) else "",
                    "node_type": node.parent.type if node.parent else "unknown",
                })

        for child in node.children:
            find_in_node(child)

    find_in_node(tree.root_node)
    return references


def supported_languages() -> list[str]:
    """Return list of supported languages."""
    return list(SYMBOL_TYPES.keys())


def supported_extensions() -> list[str]:
    """Return list of supported file extensions."""
    return list(EXT_TO_LANG.keys())
