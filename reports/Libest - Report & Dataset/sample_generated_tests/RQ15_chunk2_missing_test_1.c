/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ15_chunk2_missing_test_1.c
 */

#include <CUnit/CUnit.h>
#include "est.h"

/*
 * This prelude provides the CUnit include and the EST public header
 * so the test function below can call est_proxy_http_request and use
 * EST error constants (EST_ERR_NONE, EST_ERR_BAD_CONTENT_TYPE) as in
 * the existing test style.
 */

void rq15_chunk2_missing_test_1(void)
{
    EST_ERROR rc;

    /*
     * 1) Missing Content-Type header should be rejected with EST_ERR_BAD_CONTENT_TYPE
     */
    rc = est_proxy_http_request(NULL, NULL, "POST", "/simpleenroll", "dummycsr", 8, NULL);
    CU_ASSERT(rc == EST_ERR_BAD_CONTENT_TYPE);

    /*
     * 2) Incorrect Content-Type for PKCS#10 enroll should be rejected as bad content type
     */
    rc = est_proxy_http_request(NULL, NULL, "POST", "/simpleenroll", "dummycsr", 8, "application/incorrect");
    CU_ASSERT(rc == EST_ERR_BAD_CONTENT_TYPE);
}
