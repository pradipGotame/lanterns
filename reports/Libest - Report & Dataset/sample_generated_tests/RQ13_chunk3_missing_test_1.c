/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ13_chunk3_missing_test_1.c
 */

#include <CUnit/CUnit.h>
#include "est.h"
#include "est_server.h"
#include <openssl/x509.h>
#include <string.h>

void rq13_chunk3_missing_test_1(void)
{
    X509_REQ *req = NULL;
    /* Provide deliberately malformed PKCS#10 data to exercise the server CSR parser */
    unsigned char bad_pkcs10[] = "not-a-pkcs10-csr";

    req = est_server_parse_csr(bad_pkcs10, (int)strlen((const char *)bad_pkcs10));

    /* The server parser should reject malformed CSR data */
    CU_ASSERT(req == NULL);

    /* no cleanup required since parser returned NULL */
}
