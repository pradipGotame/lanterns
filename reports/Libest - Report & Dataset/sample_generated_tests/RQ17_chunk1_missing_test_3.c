/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ17_chunk1_missing_test_3.c
 */

#include <CUnit/CUnit.h>
#include "est.h"

/* The test harness provides a global client context `ectx` in other test
 * files; reference it here as extern to match existing test style. */
extern EST_CTX *ectx;

void rq17_chunk1_missing_test_3(void)
{
    int rc = 0;

    /*
     * Negative/path-prefix variation tests: ensure the client API
     * rejects malformed or case-variant path-segments instead of
     * allowing them to be used to construct server URIs.
     *
     * These mirror the style of existing tests that assert
     * EST_ERR_HTTP_INVALID_PATH_SEGMENT for invalid segments.
     */

    /* a path segment that attempts to include the well-known prefix */
    rc = est_client_set_server(ectx, "127.0.0.1", 8080, "/.well-known/foo");
    CU_ASSERT(rc == EST_ERR_HTTP_INVALID_PATH_SEGMENT);

    /* missing leading dot (should not be accepted as the required prefix) */
    rc = est_client_set_server(ectx, "127.0.0.1", 8080, "well-known/est");
    CU_ASSERT(rc == EST_ERR_HTTP_INVALID_PATH_SEGMENT);

    /* case-variant for ".well-known" should be rejected if case-sensitive */
    rc = est_client_set_server(ectx, "127.0.0.1", 8080, ".WELL-KNOWN");
    CU_ASSERT(rc == EST_ERR_HTTP_INVALID_PATH_SEGMENT);

    /* case-variant for "est" segment should be rejected if case-sensitive */
    rc = est_client_set_server(ectx, "127.0.0.1", 8080, "Est");
    CU_ASSERT(rc == EST_ERR_HTTP_INVALID_PATH_SEGMENT);

    /* cleanup consistent with exemplar patterns */
    if (ectx) {
        est_destroy(ectx);
    }
}
