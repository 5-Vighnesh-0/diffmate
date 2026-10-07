# Phase 4: label spot-check (5 random cases)

For each case: read the change and the labelled line. Answer: **is this really a bug** (or, for a clean case, **is the change really correct**)? Reply with case numbers that look wrong, or "all good".

## 35-hono-etag-304-header-filter (real, dev)

**PR title:** Use Headers.forEach when filtering 304 response headers

**PR description:** Iterate the response headers directly with forEach when stripping non-retained headers from a 304 response, instead of first copying the keys into an array.

`src/middleware/etag/index.ts`

```diff
@@ -121,11 +121,11 @@
           ETag: etag,
         },
       })
-      for (const key of Array.from(c.res.headers.keys())) {
+      c.res.headers.forEach((_, key) => {
         if (retainedHeaders.indexOf(key.toLowerCase()) === -1) {
           c.res.headers.delete(key)
         }
-      }
+      })
     } else {
       c.res.headers.set('ETag', etag)
     }
```

**Labelled bug:** `src/middleware/etag/index.ts` line 124: `c.res.headers.forEach((_, key) => {`

**Why:** Deleting headers while iterating the live Headers object with forEach skips entries, so some non-retained headers stay on the 304 response.

## 54-fastapi-decimal-encoder-exponent (real, dev)

**PR title:** Inline exponent check in decimal_encoder

**PR description:** Simplifies decimal_encoder by checking the Decimal tuple exponent inline instead of storing it in a temporary, and trims the docstring examples.

`fastapi/encoders.py`

```diff
@@ -34,14 +34,14 @@
     return o.isoformat()
 
 
-# Adapted from Pydantic v1
+# Taken from Pydantic v1 as is
 # TODO: pv2 should this return strings instead?
 def decimal_encoder(dec_value: Decimal) -> Union[int, float]:
     """
-    Encodes a Decimal as int if there's no exponent, otherwise float
+    Encodes a Decimal as int of there's no exponent, otherwise float
 
     This is useful when we use ConstrainedDecimal to represent Numeric(x,0)
-    where an integer (but not int typed) is used. Encoding this as a float
+    where a integer (but not int typed) is used. Encoding this as a float
     results in failed round-tripping between encode and parse.
     Our Id type is a prime example of this.
 
@@ -50,12 +50,8 @@
 
     >>> decimal_encoder(Decimal("1"))
     1
-
-    >>> decimal_encoder(Decimal("NaN"))
-    nan
     """
-    exponent = dec_value.as_tuple().exponent
-    if isinstance(exponent, int) and exponent >= 0:
+    if dec_value.as_tuple().exponent >= 0:  # type: ignore[operator]
         return int(dec_value)
     else:
         return float(dec_value)
```

**Labelled bug:** `fastapi/encoders.py` line 54: `if dec_value.as_tuple().exponent >= 0:  # type: ignore[operator]`

**Why:** For NaN/Infinity decimals as_tuple().exponent is a string ('n', 'N', 'F'), so comparing it with 0 raises TypeError in jsonable_encoder.

## 30-click-bash-dir-file-reply (real, dev)

**PR title:** Touch up dir/file branches of the bash completion script

**PR description:** Small edit to the generated bash completion function's handling of `dir` and `file` completion types.

`src/click/shell_completion.py`

```diff
@@ -102,10 +102,10 @@
         IFS=',' read type value <<< "$completion"
 
         if [[ $type == 'dir' ]]; then
-            COMPREPLY=()
+            COMREPLY=()
             compopt -o dirnames
         elif [[ $type == 'file' ]]; then
-            COMPREPLY=()
+            COMREPLY=()
             compopt -o default
         elif [[ $type == 'plain' ]]; then
             COMPREPLY+=($value)
```

**Labelled bug:** `src/click/shell_completion.py` line 105: `COMREPLY=()`

**Why:** Misspelled COMREPLY resets an unrelated variable, so COMPREPLY is not cleared before bash falls back to dirnames completion.

**Labelled bug:** `src/click/shell_completion.py` line 108: `COMREPLY=()`

**Why:** Same misspelling in the file branch: COMPREPLY is not cleared before default file completion.

## 37-requests-digest-hash-table (seeded, dev)

**PR title:** Replace digest algorithm if/elif chain with a lookup table

**PR description:** HTTPDigestAuth.build_digest_header defined a separate hashing closure for every supported algorithm. This moves the algorithm-to-hashlib mapping into a module-level table and builds a single hash_utf8 helper from it, so adding an algorithm is a one-line change.

`src/requests/auth.py`

```diff
@@ -29,6 +29,14 @@
 
 CONTENT_TYPE_FORM_URLENCODED: Final = "application/x-www-form-urlencoded"
 CONTENT_TYPE_MULTI_PART: Final = "multipart/form-data"
+
+_DIGEST_HASH_FUNCTIONS: Final = {
+    "MD5": hashlib.md5,
+    "MD5-SESS": hashlib.md5,
+    "SHA": hashlib.sha1,
+    "SHA-256": hashlib.sha256,
+    "SHA-512": hashlib.sha512,
+}
 
 
 def _basic_auth_str(username: bytes | str, password: bytes | str) -> str:
@@ -164,48 +172,20 @@
         qop = self._thread_local.chal.get("qop")
         algorithm = self._thread_local.chal.get("algorithm")
         opaque = self._thread_local.chal.get("opaque")
-        hash_utf8 = None
 
         if algorithm is None:
             _algorithm = "MD5"
         else:
             _algorithm = algorithm.upper()
-        # lambdas assume digest modules are imported at the top level
-        if _algorithm == "MD5" or _algorithm == "MD5-SESS":
 
-            def md5_utf8(x: str | bytes) -> str:
-                if isinstance(x, str):
-                    x = x.encode("utf-8")
-                return hashlib.md5(x, usedforsecurity=False).hexdigest()
+        hash_fn = _DIGEST_HASH_FUNCTIONS.get(algorithm)
+        if hash_fn is None:
+            return None
 
-            hash_utf8 = md5_utf8
-        elif _algorithm == "SHA":
-
-            def sha_utf8(x: str | bytes) -> str:
-                if isinstance(x, str):
-                    x = x.encode("utf-8")
-                return hashlib.sha1(x, usedforsecurity=False).hexdigest()
-
-            hash_utf8 = sha_utf8
-        elif _algorithm == "SHA-256":
-
-            def sha256_utf8(x: str | bytes) -> str:
-                if isinstance(x, str):
-                    x = x.encode("utf-8")
-                return hashlib.sha256(x, usedforsecurity=False).hexdigest()
-
-            hash_utf8 = sha256_utf8
-        elif _algorithm == "SHA-512":
-
-            def sha512_utf8(x: str | bytes) -> str:
-                if isinstance(x, str):
-                    x = x.encode("utf-8")
-                return hashlib.sha512(x, usedforsecurity=False).hexdigest()
-
-            hash_utf8 = sha512_utf8
-
-        if hash_utf8 is None:
-            return None
+        def hash_utf8(x: str | bytes) -> str:
+            if isinstance(x, str):
+                x = x.encode("utf-8")
+            return hash_fn(x, usedforsecurity=False).hexdigest()
 
         def KD(s: str, d: str) -> str:
             return hash_utf8(f"{s}:{d}")
```

**Labelled bug:** `src/requests/auth.py` line 181: `hash_fn = _DIGEST_HASH_FUNCTIONS.get(algorithm)`

**Why:** The table is looked up with the raw `algorithm` instead of the normalized `_algorithm`, so a missing algorithm (the RFC default MD5) or a lowercase one like 'md5' yields no hash and no Authorization header is sent.

## 58-vitest-deadline-release-operations (seeded, holdout)

**PR title:** Release tracked operations when a task deadline is cleared

**PR description:** TaskDeadline kept references to tracked operations until each one settled, even after the task finished and the timer was cleared. clear() now empties the set, and the untracking callback in track() is expanded into a block with a comment.

`packages/vitest/src/runtime/runner/deadline.ts`

```diff
@@ -45,6 +45,8 @@
   clear(): void {
     const { clearTimeout } = getSafeTimers()
     clearTimeout(this.timer)
+    // the task is done, so tracked operations can no longer affect its outcome
+    this.operations.clear()
   }
 
   /** timeout for an operation that must fail before the task does */
@@ -56,7 +58,10 @@
   track<T>(name: string, promise: Promise<T>, timeout: number, source?: Error): Promise<T> {
     const operation = { name, source, promise, endTime: now() + timeout }
     this.operations.add(operation)
-    promise.finally(() => this.operations.delete(operation)).catch(() => {})
+    // stop tracking the operation once it settles so the set only holds pending work
+    promise.finally(() => {
+      this.operations.delete(operation)
+    })
     return promise
   }
 
```

**Labelled bug:** `packages/vitest/src/runtime/runner/deadline.ts` line 62: `promise.finally(() => {`

**Why:** The promise returned by .finally() is no longer caught, so whenever a tracked operation rejects it produces an extra unhandled rejection that Vitest reports as an error.
