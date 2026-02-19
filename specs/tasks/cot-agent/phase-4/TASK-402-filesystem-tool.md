# TASK-402: Implement File System Operations Tool

## Description

Create the file system tool that provides file read/write operations through the unified tool interface with appropriate security controls.

## Requirements

- Create `FileSystemTool` class extending BaseTool:
  - Constructor accepting:
    - allowed_paths: list[str] - directories that can be accessed
    - read_only: bool = False
    - max_file_size_mb: int = 10
  - Implement `definition` property:
    - name: "file_system"
    - type: ToolType.FILE_SYSTEM
    - Parameters: operation (read/write/list/exists), path, content (for write), encoding (default utf-8)
  - Implement `execute()` method supporting operations:
    - read: Read file content (with size limit)
    - write: Write content to file (if not read_only)
    - list: List directory contents
    - exists: Check if path exists
  - Implement `validate_arguments()`:
    - Validate path is within allowed_paths
    - Check file size before reading
    - Prevent path traversal attacks

## Acceptance Criteria

- [ ] File read returns content as string
- [ ] File write creates/updates file
- [ ] Directory listing returns file names
- [ ] Path validation prevents traversal attacks
- [ ] allowed_paths restriction enforced
- [ ] Read-only mode prevents writes
- [ ] File size limit enforced
- [ ] Unit tests cover all operations and security checks

## Dependencies

- TASK-102 (for BaseTool, ToolDefinition)

## Files to Create/Modify

- `src/omniforge/tools/builtin/filesystem.py` (new)
- `tests/tools/builtin/test_filesystem.py` (new)

## Estimated Complexity

Medium (4-5 hours)

## Key Considerations

- Security is critical - validate all paths
- Use pathlib for path operations
- Consider async file I/O for large files
