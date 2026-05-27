/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ17_chunk6_missing_test_1.c
 */

#include <CUnit/CUnit.h>
#include <stdio.h>
#include <string.h>

static void rq17_chunk6_missing_test_1(void)
{
    long rv;
    char bad_url[256];

    LOG_FUNC_NM
    ;

    /* Construct a URL that appends an extra path segment to the simpleenroll URI
     * to verify exact-path enforcement (e.g., "/.well-known/est/simpleenroll/extra").
     */
    snprintf(bad_url, sizeof(bad_url), "%s/extra", US1060_PROXY_ENROLL_URL);

    rv = curl_http_post_srp(bad_url, US1060_PKCS10_CT,
        US1060_PKCS10_REQ,
        US1060_UIDPWD_GOOD, NULL, CURLAUTH_BASIC, NULL, "srp_user", "boguspwd",
        NULL, NULL);

    /* The server/proxy should reject a POST to the non-exact path. Success would be
     * indicated by rv == 0, so assert that we did not get success for the altered path.
     */
    CU_ASSERT(rv != 0);
}
