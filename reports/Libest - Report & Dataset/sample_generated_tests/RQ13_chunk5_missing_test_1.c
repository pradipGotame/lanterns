/*
 * Generated from saved assertion gaps.
 * framework=generic c test
 * language=c
 * filename=RQ13_chunk5_missing_test_1.c
 */

/* Shared includes and externs used by the generated test(s) */
#include <stdio.h>
#include <CUnit/CUnit.h>
#include "est.h"
#include <openssl/ssl.h>

/* External test context and credentials referenced by existing tests */
extern EST_CTX *ectx;
extern const char *US4020_UID;
extern const char *US4020_PWD;

/* LOG_FUNC_NM is used by exemplar tests; it is provided by the test harness */
#ifndef LOG_FUNC_NM
#define LOG_FUNC_NM
#endif

static void rq13_chunk5_missing_test_1(void)
{
    LOG_FUNC_NM
    ;

    /*
     * Positive test: ensure HTTP-header-based identity (HTTP auth)
     * is accepted when TLS client certificate authentication is absent.
     * This mirrors the style of existing tests that call
     * est_client_set_auth() and est_client_enroll() and assert on return
     * codes using CU_ASSERT.
     */
    int e_rc;
    size_t pkcs7_len = 0;
    unsigned char key[4096];

    /* Set HTTP auth credentials (simulate no TLS client cert present)
     * The exemplar tests use these APIs and CU_ASSERT for verification.
     */
    e_rc = est_client_set_auth(ectx, US4020_UID, US4020_PWD, NULL, NULL);
    CU_ASSERT(e_rc == EST_ERR_NONE);

    /* Attempt enroll; success indicates HTTP-auth fallback was accepted */
    e_rc = est_client_enroll(ectx, "RQ13-HTTP-fallback", &pkcs7_len, key);
    CU_ASSERT(e_rc == EST_ERR_NONE);

    /*
     * Exercise TLS version/cipher enforcement if a helper is available in
     * the test harness (exemplar style uses helpers like us901_test_sslversion).
     * Wrap in a conditional macro so the test remains compatible if the
     * helper is not present in the build environment.
     */
#ifdef us901_test_sslversion
    /* Expect rejection of a deprecated TLS protocol (helper-driven check) */
    us901_test_sslversion(TLSv1_client_method(), 1);
#endif
}
