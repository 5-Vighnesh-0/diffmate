// DiffMate's own ESLint config, used for every PR. The PR's configs are never loaded.
import tseslint from "typescript-eslint";

export default tseslint.config(...tseslint.configs.recommended);
