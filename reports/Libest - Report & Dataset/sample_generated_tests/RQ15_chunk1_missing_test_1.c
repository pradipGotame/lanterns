/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ15_chunk1_missing_test_1.c
 */

#include <CUnit/CUnit.h>
#include "est.h"

static void rq15_chunk1_missing_test_1(void)
{
    EST_ERROR rv;
    /* An unsupported/invalid EST URI path segment should be detected by the parser */
    const char *invalid_uri = "/.well-known/est/unsupported_segment";

    /* Call the URI parser and assert it returns the invalid-path-segment error */
    rv = est_parse_uri(invalid_uri);
    CU_ASSERT(rv == EST_ERR_HTTP_INVALID_PATH_SEGMENT);
}
